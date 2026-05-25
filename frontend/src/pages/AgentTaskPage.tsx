import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { agentApi, knowledgeBaseApi, type AgentStep, type AgentTask, type KnowledgeBase } from '../api/client';

const statusClass: Record<string, string> = {
  completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  failed: 'bg-rose-50 text-rose-700 border-rose-200',
  cancelled: 'bg-slate-100 text-slate-600 border-slate-200',
  paused: 'bg-violet-50 text-violet-700 border-violet-200',
  running: 'bg-sky-50 text-sky-700 border-sky-200',
  planning: 'bg-sky-50 text-sky-700 border-sky-200',
  needs_approval: 'bg-amber-50 text-amber-700 border-amber-200',
  pending: 'bg-gray-50 text-gray-600 border-gray-200',
};

const statusText: Record<string, string> = {
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
  paused: 'Paused',
  running: 'Running',
  planning: 'Planning',
  needs_approval: 'Needs approval',
  pending: 'Pending',
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

function statusBadge(status: string) {
  return `inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${statusClass[status] ?? statusClass.pending}`;
}

function StepStatus({ step }: { step: AgentStep }) {
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-1 h-2.5 w-2.5 rounded-full ${
        step.status === 'completed' ? 'bg-emerald-500' :
        step.status === 'failed' ? 'bg-rose-500' :
        step.status === 'running' ? 'bg-sky-500' :
        step.status === 'needs_approval' ? 'bg-amber-500' :
        step.status === 'cancelled' ? 'bg-slate-400' : 'bg-gray-300'
      }`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-gray-900">{step.description}</p>
          <span className={statusBadge(step.status)}>{statusText[step.status] ?? step.status}</span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
          {step.tool_name ? <span>{step.tool_name}</span> : null}
          {step.latency_ms ? <span>{step.latency_ms.toFixed(0)} ms</span> : null}
          {step.error ? <span className="text-rose-600">{step.error}</span> : null}
        </div>
      </div>
    </div>
  );
}

export default function AgentTaskPage() {
  const { kbId } = useParams<{ kbId: string }>();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState(kbId ?? '');
  const [goal, setGoal] = useState('根据知识库里的部署文档，生成一份上线 checklist，并指出缺失的监控项。');
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [activeTask, setActiveTask] = useState<AgentTask | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const loadTasks = useCallback(async () => {
    const data = await agentApi.listTasks();
    setTasks(data);
    if (!activeTask && data.length) setActiveTask(data[0]);
  }, [activeTask]);

  const refreshActive = useCallback(async () => {
    if (!activeTask) return;
    const task = await agentApi.getTask(activeTask.id);
    setActiveTask(task);
    const data = await agentApi.listTasks();
    setTasks(data);
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
    }, 1400);
    return () => window.clearInterval(timer);
  }, [activeTask?.id, activeTask?.status, refreshActive]);

  const currentReport = useMemo(() => activeTask?.artifacts?.[0], [activeTask]);
  const sources = useMemo(() => (activeTask?.result?.sources as Record<string, unknown>[] | undefined) ?? [], [activeTask]);
  const tokenUsage = activeTask?.result?.token_usage as Record<string, unknown> | undefined;
  const plannerMode = String(activeTask?.result?.planner_mode ?? 'unknown');
  const completedSteps = activeTask?.steps?.filter((step) => step.status === 'completed').length ?? 0;
  const totalSteps = activeTask?.steps?.length ?? 0;
  const progress = totalSteps ? Math.round((completedSteps / totalSteps) * 100) : 0;
  const canPause = activeTask && ['pending', 'planning', 'running'].includes(activeTask.status);
  const canResume = activeTask && ['paused', 'failed'].includes(activeTask.status);
  const canCancel = activeTask && !['completed', 'failed', 'cancelled'].includes(activeTask.status);

  const withAction = async (name: string, action: () => Promise<AgentTask>) => {
    setBusyAction(name);
    try {
      const task = await action();
      setActiveTask(task);
      await loadTasks();
    } finally {
      setBusyAction(null);
    }
  };

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

  const copyStep = async (step: AgentStep) => {
    await navigator.clipboard.writeText(compactJson({
      tool: step.tool_name,
      input: step.tool_input,
      output: step.observation,
      error: step.error,
    }));
  };

  return (
    <div className="flex flex-1 h-[calc(100vh-4rem)] overflow-hidden bg-gray-50">
      <aside className="w-80 shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-100">
          <h1 className="text-base font-semibold text-gray-950">Agent Tasks</h1>
          <p className="mt-1 text-xs text-gray-500">Plan, execute, review evidence, and recover safely.</p>
        </div>
        <div className="p-3 border-b border-gray-100">
          <select
            value={selectedKbId}
            onChange={(e) => setSelectedKbId(e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
          >
            <option value="">No knowledge base</option>
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
              className={`mb-1 w-full rounded-md border p-3 text-left transition ${
                activeTask?.id === task.id ? 'border-primary-300 bg-primary-50' : 'border-transparent hover:bg-gray-50'
              }`}
            >
              <div className="line-clamp-2 text-sm font-medium text-gray-900">{task.goal}</div>
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className={statusBadge(task.status)}>{statusText[task.status] ?? task.status}</span>
                <span className="text-xs text-gray-400">{task.steps?.length ?? 0} steps</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto">
          <section className="border-b border-gray-200 bg-white px-6 py-4">
            <div className="mx-auto max-w-6xl">
              <div className="flex gap-3">
                <textarea
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  className="min-h-20 flex-1 resize-none rounded-md border border-gray-300 px-3 py-2 text-sm leading-6 text-gray-900"
                />
                <button
                  onClick={createTask}
                  disabled={loading || !goal.trim()}
                  className="h-10 rounded-md bg-primary-600 px-4 text-sm font-medium text-white disabled:bg-gray-300"
                >
                  {loading ? 'Starting' : 'Run'}
                </button>
              </div>
            </div>
          </section>

          {!activeTask ? (
            <div className="flex h-[calc(100vh-12rem)] items-center justify-center text-gray-400">
              Create or select an Agent task.
            </div>
          ) : (
            <div className="mx-auto grid max-w-6xl grid-cols-[minmax(0,1fr)_360px] gap-6 px-6 py-6">
              <section className="min-w-0 space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={statusBadge(activeTask.status)}>{statusText[activeTask.status] ?? activeTask.status}</span>
                      <span className="text-xs text-gray-500">{progress}% complete</span>
                    </div>
                    <h2 className="mt-3 text-xl font-semibold text-gray-950">{activeTask.goal}</h2>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {canPause ? (
                      <button
                        onClick={() => withAction('pause', () => agentApi.pauseTask(activeTask.id, 'paused from workspace'))}
                        disabled={busyAction !== null}
                        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700"
                      >
                        Pause
                      </button>
                    ) : null}
                    {canResume ? (
                      <button
                        onClick={() => withAction('resume', () => agentApi.resumeTask(activeTask.id))}
                        disabled={busyAction !== null}
                        className="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white"
                      >
                        Resume
                      </button>
                    ) : null}
                    {canCancel ? (
                      <button
                        onClick={() => withAction('cancel', () => agentApi.cancelTask(activeTask.id, 'cancelled from workspace'))}
                        disabled={busyAction !== null}
                        className="rounded-md border border-rose-200 bg-white px-3 py-1.5 text-sm text-rose-700"
                      >
                        Cancel
                      </button>
                    ) : null}
                    <button onClick={refreshActive} className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700">
                      Refresh
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <div className="rounded-md border border-gray-200 bg-white p-3">
                    <div className="text-xs text-gray-500">Planner</div>
                    <div className="mt-1 text-sm font-semibold text-gray-950">{plannerMode}</div>
                  </div>
                  <div className="rounded-md border border-gray-200 bg-white p-3">
                    <div className="text-xs text-gray-500">Tool calls</div>
                    <div className="mt-1 text-sm font-semibold text-gray-950">{activeTask.tool_calls?.length ?? 0}</div>
                  </div>
                  <div className="rounded-md border border-gray-200 bg-white p-3">
                    <div className="text-xs text-gray-500">Tokens</div>
                    <div className="mt-1 text-sm font-semibold text-gray-950">{String(tokenUsage?.total_tokens ?? 0)}</div>
                  </div>
                  <div className="rounded-md border border-gray-200 bg-white p-3">
                    <div className="text-xs text-gray-500">Est. cost</div>
                    <div className="mt-1 text-sm font-semibold text-gray-950">{formatCost(tokenUsage?.estimated_cost_usd)}</div>
                  </div>
                </div>

                {activeTask.status === 'needs_approval' ? (
                  <div className="flex items-center gap-3 rounded-md border border-amber-200 bg-amber-50 p-4">
                    <div className="flex-1">
                      <div className="text-sm font-medium text-amber-900">Approval required</div>
                      <div className="mt-1 text-sm text-amber-800">A write or external action is waiting for confirmation.</div>
                    </div>
                    <button
                      onClick={() => withAction('approve', () => agentApi.approveTask(activeTask.id, 'approved from workspace'))}
                      className="rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => withAction('reject', () => agentApi.rejectTask(activeTask.id, 'rejected from workspace'))}
                      className="rounded-md border border-amber-300 bg-white px-3 py-1.5 text-sm text-amber-900"
                    >
                      Reject
                    </button>
                  </div>
                ) : null}

                {activeTask.error ? (
                  <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                    {activeTask.error}
                  </div>
                ) : null}

                {currentReport ? (
                  <article className="rounded-md border border-gray-200 bg-white p-5 text-sm leading-7 text-gray-800 whitespace-pre-wrap">
                    {currentReport.content}
                  </article>
                ) : (
                  <div className="rounded-md border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500">
                    The report will appear here when the Agent has enough evidence.
                  </div>
                )}

                {sources.length ? (
                  <section className="rounded-md border border-gray-200 bg-white p-4">
                    <h3 className="text-sm font-semibold text-gray-950">Evidence</h3>
                    <div className="mt-3 space-y-2">
                      {sources.map((source, index) => {
                        const documentId = String(source.document_id ?? '');
                        const chunkId = String(source.chunk_id ?? '');
                        const kbLink = activeTask.knowledge_base_id ? `/knowledge-bases/${activeTask.knowledge_base_id}/documents` : '#';
                        const apiLink = documentId && chunkId ? `/api/v1/documents/${documentId}/chunks/${chunkId}` : kbLink;
                        return (
                          <div key={`${documentId}-${chunkId}-${index}`} className="rounded-md border border-gray-100 bg-gray-50 p-3">
                            <div className="flex items-center justify-between gap-2">
                              <a href={kbLink} className="text-sm font-medium text-primary-700 hover:underline">
                                [{index + 1}] {String(source.document_title ?? source.title ?? 'Untitled source')}
                              </a>
                              <a href={apiLink} className="text-xs text-gray-500 hover:text-primary-700" target="_blank" rel="noreferrer">
                                Open chunk
                              </a>
                            </div>
                            <div className="mt-1 text-xs text-gray-500">
                              rank {String(source.rank ?? index + 1)} · score {Number(source.score ?? 0).toFixed(3)}
                            </div>
                            <p className="mt-2 line-clamp-3 text-sm leading-6 text-gray-700">{String(source.text ?? '')}</p>
                          </div>
                        );
                      })}
                    </div>
                  </section>
                ) : null}
              </section>

              <aside className="space-y-4">
                <section className="rounded-md border border-gray-200 bg-white p-4">
                  <h3 className="text-sm font-semibold text-gray-950">Execution</h3>
                  <div className="mt-4 space-y-4">
                    {activeTask.steps?.map((step) => (
                      <div key={step.id} className="border-b border-gray-100 pb-4 last:border-b-0 last:pb-0">
                        <StepStatus step={step} />
                        <div className="mt-3 flex items-center gap-2 pl-5">
                          {['failed', 'cancelled'].includes(step.status) ? (
                            <button
                              onClick={() => withAction(`retry-${step.id}`, () => agentApi.retryStep(activeTask.id, step.id))}
                              className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs text-gray-700"
                            >
                              Retry from here
                            </button>
                          ) : null}
                          <button
                            onClick={() => copyStep(step)}
                            className="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs text-gray-500"
                          >
                            Copy details
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                {activeTask.approval_events?.length ? (
                  <section className="rounded-md border border-gray-200 bg-white p-4">
                    <h3 className="text-sm font-semibold text-gray-950">Approvals</h3>
                    <div className="mt-3 space-y-2">
                      {activeTask.approval_events.map((event) => (
                        <div key={event.id} className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">
                          <div className="font-medium">{event.action} {event.tool_name ? `· ${event.tool_name}` : ''}</div>
                          {event.note ? <div className="mt-1 text-amber-800">{event.note}</div> : null}
                        </div>
                      ))}
                    </div>
                  </section>
                ) : null}

                <section className="rounded-md border border-gray-200 bg-white p-4">
                  <details>
                    <summary className="cursor-pointer text-sm font-semibold text-gray-950">Plan details</summary>
                    <pre className="mt-3 max-h-72 overflow-auto rounded-md bg-gray-50 p-3 text-xs text-gray-700">
                      {compactJson(activeTask.plan)}
                    </pre>
                  </details>
                </section>
              </aside>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
