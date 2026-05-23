import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { agentApi, knowledgeBaseApi, type AgentTask, type KnowledgeBase } from '../api/client';

const statusClass: Record<string, string> = {
  completed: 'bg-green-50 text-green-700 border-green-200',
  failed: 'bg-red-50 text-red-700 border-red-200',
  running: 'bg-blue-50 text-blue-700 border-blue-200',
  planning: 'bg-blue-50 text-blue-700 border-blue-200',
  needs_approval: 'bg-amber-50 text-amber-700 border-amber-200',
  pending: 'bg-gray-50 text-gray-600 border-gray-200',
};

function compactJson(value: unknown): string {
  if (!value) return '';
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatCost(value: unknown): string {
  const numeric = typeof value === 'number' ? value : Number(value ?? 0);
  return `$${numeric.toFixed(6)}`;
}

export default function AgentTaskPage() {
  const { kbId } = useParams<{ kbId: string }>();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState(kbId ?? '');
  const [goal, setGoal] = useState('根据知识库里的部署文档，生成一份上线 checklist，并指出缺失的监控项。');
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [activeTask, setActiveTask] = useState<AgentTask | null>(null);
  const [loading, setLoading] = useState(false);

  const loadTasks = useCallback(async () => {
    const data = await agentApi.listTasks();
    setTasks(data);
    if (!activeTask && data.length) setActiveTask(data[0]);
  }, [activeTask]);

  useEffect(() => {
    knowledgeBaseApi.list().then((data) => {
      setKbs(data.knowledge_bases);
      if (!selectedKbId && data.knowledge_bases[0]) setSelectedKbId(data.knowledge_bases[0].id);
    }).catch(console.error);
    loadTasks().catch(console.error);
  }, [loadTasks, selectedKbId]);

  useEffect(() => {
    if (!activeTask || !['pending', 'planning', 'running'].includes(activeTask.status)) return undefined;
    const timer = window.setInterval(() => {
      refreshActive().catch(console.error);
    }, 1500);
    return () => window.clearInterval(timer);
  }, [activeTask?.id, activeTask?.status]);

  const currentReport = useMemo(() => activeTask?.artifacts?.[0], [activeTask]);
  const sources = useMemo(() => (activeTask?.result?.sources as Record<string, unknown>[] | undefined) ?? [], [activeTask]);
  const toolCallByStep = useMemo(() => {
    const pairs = new Map<string, NonNullable<AgentTask['tool_calls']>[number]>();
    activeTask?.tool_calls?.forEach((call) => {
      if (call.step_id) pairs.set(call.step_id, call);
    });
    return pairs;
  }, [activeTask]);

  const createTask = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    try {
      const task = await agentApi.createTask({
        goal,
        knowledge_base_id: selectedKbId || undefined,
        auto_run: true,
      });
      setActiveTask(task);
      await loadTasks();
    } finally {
      setLoading(false);
    }
  };

  const refreshActive = async () => {
    if (!activeTask) return;
    const task = await agentApi.getTask(activeTask.id);
    setActiveTask(task);
    await loadTasks();
  };

  const approveActive = async () => {
    if (!activeTask) return;
    const task = await agentApi.approveTask(activeTask.id, 'approved from trace UI');
    setActiveTask(task);
    await loadTasks();
  };

  const rejectActive = async () => {
    if (!activeTask) return;
    const task = await agentApi.rejectTask(activeTask.id, 'rejected from trace UI');
    setActiveTask(task);
    await loadTasks();
  };

  return (
    <div className="flex flex-1 h-[calc(100vh-4rem)] overflow-hidden bg-gray-50">
      <aside className="w-72 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-100">
          <h1 className="text-base font-semibold text-gray-900">Agent Tasks</h1>
          <p className="text-xs text-gray-500 mt-1">任务规划、工具调用和 trace 回放</p>
        </div>
        <div className="p-3 border-b border-gray-100">
          <select
            value={selectedKbId}
            onChange={(e) => setSelectedKbId(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white"
          >
            <option value="">不指定知识库</option>
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id}>{kb.name}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {tasks.map((task) => (
            <button
              key={task.id}
              onClick={() => setActiveTask(task)}
              className={`w-full text-left p-3 rounded-lg mb-1 border ${
                activeTask?.id === task.id ? 'border-primary-300 bg-primary-50' : 'border-transparent hover:bg-gray-50'
              }`}
            >
              <div className="text-sm font-medium text-gray-800 line-clamp-2">{task.goal}</div>
              <div className="mt-2 flex items-center justify-between">
                <span className={`text-xs px-2 py-0.5 rounded-full border ${statusClass[task.status] ?? statusClass.pending}`}>
                  {task.status}
                </span>
                <span className="text-xs text-gray-400">{task.steps?.length ?? 0} steps</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex gap-3">
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="flex-1 min-h-20 px-3 py-2 text-sm border border-gray-300 rounded-lg resize-none"
            />
            <button
              onClick={createTask}
              disabled={loading || !goal.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium disabled:bg-gray-300"
            >
              {loading ? '运行中' : '运行 Agent'}
            </button>
          </div>
        </div>

        <div className="flex-1 grid grid-cols-[minmax(0,1fr)_420px] overflow-hidden">
          <section className="overflow-y-auto p-6">
            {!activeTask ? (
              <div className="h-full flex items-center justify-center text-gray-400">创建或选择一个 Agent 任务</div>
            ) : (
              <div className="max-w-3xl">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">任务结果</h2>
                    <p className="text-sm text-gray-500 mt-1">{activeTask.goal}</p>
                  </div>
                  <button onClick={refreshActive} className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white">
                    刷新
                  </button>
                </div>

                <div className={`inline-flex text-xs px-2 py-1 rounded-full border mb-4 ${statusClass[activeTask.status] ?? statusClass.pending}`}>
                  {activeTask.status}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                  <div className="bg-white border border-gray-200 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Planner</div>
                    <div className="mt-1 text-sm font-semibold text-gray-900">
                      {String(activeTask.result?.planner_mode ?? 'unknown')}
                    </div>
                  </div>
                  <div className="bg-white border border-gray-200 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Tool calls</div>
                    <div className="mt-1 text-sm font-semibold text-gray-900">{activeTask.tool_calls?.length ?? 0}</div>
                  </div>
                  <div className="bg-white border border-gray-200 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Tokens</div>
                    <div className="mt-1 text-sm font-semibold text-gray-900">
                      {String((activeTask.result?.token_usage as Record<string, unknown> | undefined)?.total_tokens ?? 0)}
                    </div>
                  </div>
                  <div className="bg-white border border-gray-200 rounded-lg p-3">
                    <div className="text-xs text-gray-500">Est. cost</div>
                    <div className="mt-1 text-sm font-semibold text-gray-900">
                      {formatCost((activeTask.result?.token_usage as Record<string, unknown> | undefined)?.estimated_cost_usd)}
                    </div>
                  </div>
                </div>

                {activeTask.status === 'needs_approval' && (
                  <div className="mb-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
                    <span className="text-sm text-amber-800 flex-1">This task is waiting for human approval.</span>
                    <button onClick={approveActive} className="px-3 py-1.5 text-sm rounded-lg bg-amber-600 text-white">
                      Approve
                    </button>
                    <button onClick={rejectActive} className="px-3 py-1.5 text-sm rounded-lg border border-amber-300 bg-white text-amber-800">
                      Reject
                    </button>
                  </div>
                )}

                {activeTask.error && (
                  <div className="mb-4 p-3 rounded-lg border border-red-200 bg-red-50 text-sm text-red-700">
                    {activeTask.error}
                  </div>
                )}

                {currentReport ? (
                  <>
                    <article className="bg-white border border-gray-200 rounded-lg p-5 whitespace-pre-wrap text-sm leading-7 text-gray-800">
                      {currentReport.content}
                    </article>
                    {sources.length ? (
                      <div className="mt-4 bg-white border border-gray-200 rounded-lg p-4">
                        <h3 className="text-sm font-semibold text-gray-900 mb-3">Sources</h3>
                        <div className="space-y-2">
                          {sources.map((source, index) => {
                            const documentId = String(source.document_id ?? '');
                            const chunkId = String(source.chunk_id ?? '');
                            const kbLink = activeTask.knowledge_base_id
                              ? `/knowledge-bases/${activeTask.knowledge_base_id}/documents`
                              : '#';
                            const apiLink = documentId && chunkId
                              ? `/api/v1/documents/${documentId}/chunks/${chunkId}`
                              : kbLink;
                            return (
                              <div key={`${documentId}-${chunkId}-${index}`} className="rounded border border-gray-100 bg-gray-50 p-3 text-xs">
                                <div className="flex items-center justify-between gap-2">
                                  <a href={kbLink} className="font-medium text-primary-700 hover:underline">
                                    [{index + 1}] {String(source.document_title ?? source.title ?? 'Untitled source')}
                                  </a>
                                  <a href={apiLink} className="text-gray-500 hover:text-primary-700" target="_blank" rel="noreferrer">
                                    chunk
                                  </a>
                                </div>
                                <div className="mt-1 text-gray-500">
                                  rank {String(source.rank ?? index + 1)} · score {Number(source.score ?? 0).toFixed(3)}
                                </div>
                                <div className="mt-2 line-clamp-2 text-gray-700">{String(source.text ?? '')}</div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <pre className="bg-white border border-gray-200 rounded-lg p-5 text-sm overflow-x-auto">
                    {compactJson(activeTask.result)}
                  </pre>
                )}
              </div>
            )}
          </section>

          <aside className="border-l border-gray-200 bg-white overflow-y-auto p-4">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">Trace Timeline</h2>
            {activeTask?.approval_events?.length ? (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
                <div className="text-xs font-semibold text-amber-800 mb-2">Approval events</div>
                <div className="space-y-1">
                  {activeTask.approval_events.map((event) => (
                    <div key={event.id} className="text-xs text-amber-900">
                      {event.action} {event.tool_name ? `· ${event.tool_name}` : ''} {event.note ? `· ${event.note}` : ''}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="space-y-3">
              {activeTask?.steps?.map((step) => {
                const call = toolCallByStep.get(step.id);
                const tokenUsage = call?.token_usage as Record<string, unknown> | undefined;
                return (
                <div key={step.id} className="border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-gray-500">#{step.step_index + 1}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${statusClass[step.status] ?? statusClass.pending}`}>
                      {step.status}
                    </span>
                  </div>
                  <div className="mt-2 text-sm font-medium text-gray-800">{step.description}</div>
                  {step.tool_name && (
                    <div className="mt-2 text-xs text-primary-700 bg-primary-50 border border-primary-100 rounded px-2 py-1">
                      tool: {step.tool_name} · {step.latency_ms ? `${step.latency_ms.toFixed(0)}ms` : 'pending'}
                    </div>
                  )}
                  {tokenUsage && (
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                      <div className="rounded border border-gray-100 bg-gray-50 px-2 py-1">
                        tokens: {String(tokenUsage.total_tokens ?? 0)}
                      </div>
                      <div className="rounded border border-gray-100 bg-gray-50 px-2 py-1">
                        cost: {formatCost(tokenUsage.estimated_cost_usd)}
                      </div>
                    </div>
                  )}
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-gray-500">input / output</summary>
                    <pre className="mt-2 max-h-56 overflow-auto text-xs bg-gray-50 border border-gray-100 rounded p-2">
                      {compactJson({ input: step.tool_input, output: step.observation, token_usage: tokenUsage, error: step.error })}
                    </pre>
                  </details>
                </div>
              );})}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
