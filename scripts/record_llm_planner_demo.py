"""Record one real LLM planner demo artifact for README/interview evidence."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.agent_planner import AgentPlanner


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", default="根据知识库里的部署文档，生成一份上线 checklist，并指出缺失的监控项。")
    parser.add_argument("--knowledge-base-id", default="00000000-0000-0000-0000-000000000001")
    parser.add_argument("--output", default="docs/assets/llm-planner-demo.json")
    args = parser.parse_args()

    settings = get_settings()
    original_mode = settings.AGENT_PLANNER_MODE
    settings.AGENT_PLANNER_MODE = "llm_fallback"
    fallback_plan = [
        {
            "description": "Create a structured Markdown report with citations.",
            "tool_name": "create_report",
            "tool_input": {
                "title": "Agent Task Report",
                "sections": [{"heading": "Task", "content": args.goal}],
                "sources": [],
            },
        }
    ]

    try:
        result = AgentPlanner().plan(args.goal, uuid.UUID(args.knowledge_base_id), fallback_plan)
    finally:
        settings.AGENT_PLANNER_MODE = original_mode

    artifact = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "provider": settings.LLM_PROVIDER,
        "model": settings.AGENT_PLANNER_MODEL or "provider_default",
        "goal": args.goal,
        "planner_mode": result.mode,
        "planner_error": result.error,
        "plan": result.plan,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if result.mode == "llm" else 2


if __name__ == "__main__":
    raise SystemExit(main())
