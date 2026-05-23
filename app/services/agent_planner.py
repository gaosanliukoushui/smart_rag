"""LLM-assisted planner for Agent tasks."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.services.agent_tools import registry


@dataclass
class PlannerResult:
    """Planner output with provenance."""

    plan: list[dict[str, Any]]
    mode: str
    error: str | None = None


class AgentPlanner:
    """Generate and validate tool plans.

    The LLM planner is intentionally constrained: it may only choose registered
    tools, and every tool input is validated against the tool JSON schema.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def plan(
        self,
        goal: str,
        knowledge_base_id: uuid.UUID | None,
        fallback_plan: list[dict[str, Any]],
    ) -> PlannerResult:
        mode = self.settings.AGENT_PLANNER_MODE.lower()
        if mode == "rule":
            return PlannerResult(plan=fallback_plan, mode="rule")

        try:
            raw_plan = self._call_llm(goal, knowledge_base_id)
            plan = self.validate_plan(raw_plan, knowledge_base_id, goal)
            if not plan:
                raise ValueError("LLM planner returned an empty plan")
            return PlannerResult(plan=plan, mode="llm")
        except Exception as exc:
            if mode == "llm":
                raise
            return PlannerResult(plan=fallback_plan, mode="rule_fallback", error=str(exc))

    def validate_plan(
        self,
        raw_plan: list[dict[str, Any]],
        knowledge_base_id: uuid.UUID | None,
        goal: str,
    ) -> list[dict[str, Any]]:
        """Validate planner JSON and normalize required tool inputs."""
        validated: list[dict[str, Any]] = []
        max_steps = self.settings.AGENT_PLANNER_MAX_STEPS
        kb_id = str(knowledge_base_id) if knowledge_base_id else None

        for item in raw_plan[:max_steps]:
            tool_name = item.get("tool_name")
            if not tool_name:
                continue
            spec = registry.get(tool_name)
            tool_input = dict(item.get("tool_input") or {})

            if kb_id and tool_name in {"search_kb", "list_documents", "ask_rag"}:
                tool_input.setdefault("knowledge_base_id", kb_id)
            if tool_name == "search_kb":
                tool_input.setdefault("query", goal)
                tool_input.setdefault("top_k", 5)
            elif tool_name == "ask_rag":
                tool_input.setdefault("question", goal)
                tool_input.setdefault("top_k", 5)
            elif tool_name == "list_documents":
                tool_input.setdefault("limit", 20)
            elif tool_name == "create_report":
                tool_input.setdefault("title", "Agent Task Report")
                tool_input.setdefault("sections", [{"heading": "Task", "content": goal}])
                tool_input.setdefault("sources", [])

            spec.input_model.model_validate(tool_input)
            validated.append(
                {
                    "description": str(item.get("description") or f"Run {tool_name}.")[:500],
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                }
            )

        if not any(step["tool_name"] == "create_report" for step in validated):
            validated.append(
                {
                    "description": "Create a structured Markdown report with citations.",
                    "tool_name": "create_report",
                    "tool_input": {
                        "title": "Agent Task Report",
                        "sections": [{"heading": "Task", "content": goal}],
                        "sources": [],
                    },
                }
            )
        return validated

    def _call_llm(self, goal: str, knowledge_base_id: uuid.UUID | None) -> list[dict[str, Any]]:
        client = OpenAI(api_key=self._api_key(), base_url=self._base_url())
        response = client.chat.completions.create(
            model=self._model(),
            temperature=0,
            max_tokens=1200,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "goal": goal,
                            "knowledge_base_id": str(knowledge_base_id) if knowledge_base_id else None,
                            "available_tools": self._tool_specs_for_prompt(),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        content = response.choices[0].message.content or ""
        return self._extract_plan_json(content)

    def _system_prompt(self) -> str:
        return (
            "You are a planning module for a knowledge-base Agent. "
            "Return ONLY JSON with shape {\"steps\": [...]}. "
            "Each step must contain description, tool_name, and tool_input. "
            "Use only the provided tools. Prefer 4-7 steps. "
            "All write, publish, delete, send, or external actions must use a tool that requires approval. "
            "Do not invent document ids unless they are provided by prior context."
        )

    def _tool_specs_for_prompt(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "requires_approval": spec.requires_approval,
                "input_schema": spec.input_schema,
            }
            for spec in registry.list_specs()
        ]

    def _extract_plan_json(self, content: str) -> list[dict[str, Any]]:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise ValueError("Planner response did not contain a JSON object")
        data = json.loads(match.group(0))
        steps = data.get("steps")
        if not isinstance(steps, list):
            raise ValueError("Planner JSON must contain a steps array")
        return steps

    def _model(self) -> str:
        if self.settings.AGENT_PLANNER_MODEL:
            return self.settings.AGENT_PLANNER_MODEL
        if self.settings.LLM_PROVIDER == "deepseek":
            return self.settings.DEEPSEEK_MODEL
        if self.settings.LLM_PROVIDER == "qwen":
            return self.settings.QWEN_MODEL
        if self.settings.LLM_PROVIDER == "openai":
            return self.settings.OPENAI_MODEL
        if self.settings.LLM_PROVIDER == "ollama":
            return self.settings.OLLAMA_MODEL
        return self.settings.OPENAI_MODEL

    def _api_key(self) -> str:
        if self.settings.LLM_PROVIDER == "deepseek":
            return self.settings.DEEPSEEK_API_KEY
        if self.settings.LLM_PROVIDER == "qwen":
            return self.settings.QWEN_API_KEY
        if self.settings.LLM_PROVIDER == "ollama":
            return "ollama"
        return self.settings.OPENAI_API_KEY

    def _base_url(self) -> str | None:
        if self.settings.LLM_PROVIDER == "deepseek":
            return self.settings.DEEPSEEK_BASE_URL
        if self.settings.LLM_PROVIDER == "qwen":
            return self.settings.QWEN_BASE_URL
        if self.settings.LLM_PROVIDER == "ollama":
            return f"{self.settings.OLLAMA_BASE_URL.rstrip('/')}/v1"
        return None
