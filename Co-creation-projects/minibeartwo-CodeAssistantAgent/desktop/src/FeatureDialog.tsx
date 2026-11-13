import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import type { HomeAction } from './ClientHome';
import type { ModelSettings, Task, TaskEvent, Workspace } from './types';
import './feature-dialog.css';

const statusLabels: Record<string, string> = {
  queued: '等待执行',
  running: '正在处理',
  waiting_review: '等待审阅',
  completed: '已完成',
  failed: '执行失败',
  cancelled: '已取消',
  interrupted: '已中断',
  budget_exhausted: '达到预算',
  rejected: '已拒绝',
};
const patchLabels: Record<string, string> = {
  proposed: '待审阅',
  applied: '已应用',
  rejected: '已拒绝',
  reverted: '已撤销',
  recovery_required: '需要恢复',
  conflicted: '文件冲突',
};

export function useDialogFocus<T extends HTMLElement>(onClose: () => void) {
  const ref = useRef<T>(null);
  const close = useRef(onClose);
  useEffect(() => {
    close.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const previous = document.activeElement;
    const dialog = ref.current;
    if (!dialog) return;
    const controls = () =>
      Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex="0"]',
        ),
      ).filter((element) => element.getClientRects().length > 0);
    (controls()[0] || dialog).focus();
    const keydown = (event: KeyboardEvent) => {
      const dialogs = document.querySelectorAll('[role="dialog"]');
      if (dialogs.item(dialogs.length - 1) !== dialog) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        close.current();
      } else if (event.key === 'Tab') {
        const entries = controls();
        const first = entries[0];
        const last = entries.at(-1);
        if (!first) {
          event.preventDefault();
          dialog.focus();
        } else if (
          event.shiftKey &&
          (document.activeElement === first || !dialog.contains(document.activeElement))
        ) {
          event.preventDefault();
          last?.focus();
        } else if (
          !event.shiftKey &&
          (document.activeElement === last || !dialog.contains(document.activeElement))
        ) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener('keydown', keydown);
    return () => {
      document.removeEventListener('keydown', keydown);
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, []);
  return ref;
}

export interface FeatureDialogProps {
  action: HomeAction;
  workspace: Workspace;
  selectedFile: string | null;
  settings: ModelSettings | null;
  task: Task | null;
  tasks: Task[];
  prompt: string;
  onPromptChange: (value: string) => void;
  testEnabled: boolean;
  testCommand: string;
  onTestsChange: (value: boolean) => void;
  onTestCommandChange: (value: string) => void;
  busy: boolean;
  sending: boolean;
  operationPending: boolean;
  activity: TaskEvent[];
  logs: string;
  error: string;
  onClose: () => void;
  onSettings: () => void;
  onStart: () => void;
  onLoadTask: (id: string) => void;
  onDeleteTask: (id: string) => void;
  onNewTask: () => void;
  onReview: (patchId: string, accept: boolean) => void;
  onUndo: (patchId: string) => void;
  onCancel: () => void;
  onResumeTask: () => void;
}

const finishedStatuses = new Set([
  'completed',
  'failed',
  'cancelled',
  'interrupted',
  'budget_exhausted',
  'rejected',
]);

function TaskHistory({
  task,
  tasks,
  busy,
  sending,
  operationPending,
  onLoadTask,
  onNewTask,
  onDeleteTask,
}: Pick<
  FeatureDialogProps,
  | 'task'
  | 'tasks'
  | 'busy'
  | 'sending'
  | 'operationPending'
  | 'onLoadTask'
  | 'onNewTask'
  | 'onDeleteTask'
>) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const locked = busy || sending || operationPending;
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [open]);
  const choose = (id?: string) => {
    setOpen(false);
    if (id) onLoadTask(id);
    else onNewTask();
    trigger.current?.focus();
  };
  return (
    <div
      className="feature-history"
      ref={root}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && open) {
          event.preventDefault();
          event.stopPropagation();
          setOpen(false);
          trigger.current?.focus();
        }
      }}
    >
      <div className="feature-history-picker">
        <span className="feature-history-label">任务记录</span>
        <button
          ref={trigger}
          type="button"
          className="task-history-trigger"
          aria-label="历史任务"
          aria-expanded={open}
          aria-controls={menuId}
          data-task-id={task?.id || ''}
          disabled={sending || operationPending}
          onClick={() => setOpen((previous) => !previous)}
        >
          <span>
            {task
              ? `${statusLabels[task.status] || task.status} · ${task.prompt.slice(0, 52)}`
              : '新任务'}
          </span>
          <span aria-hidden="true">{open ? '▴' : '▾'}</span>
        </button>
        {open && (
          <div id={menuId} className="task-history-menu">
            <ul aria-label="任务记录列表">
              <li>
                <button
                  className="task-history-select"
                  type="button"
                  disabled={locked}
                  aria-current={!task ? 'true' : undefined}
                  onClick={() => choose()}
                >
                  新任务
                </button>
              </li>
              {tasks.map((item) => (
                <li key={item.id} className="task-history-row" data-task-id={item.id}>
                  <button
                    className="task-history-select"
                    type="button"
                    disabled={locked}
                    aria-current={task?.id === item.id ? 'true' : undefined}
                    title={item.prompt}
                    onClick={() => choose(item.id)}
                  >
                    <span>{statusLabels[item.status] || item.status}</span>
                    <span>{item.prompt.slice(0, 80)}</span>
                  </button>
                  <button
                    className="task-history-delete"
                    type="button"
                    aria-label={`删除任务：${item.prompt.slice(0, 52)}`}
                    title={
                      finishedStatuses.has(item.status)
                        ? '删除此任务记录'
                        : '请先停止任务，再删除记录'
                    }
                    disabled={sending || operationPending || !finishedStatuses.has(item.status)}
                    onClick={() => onDeleteTask(item.id)}
                  >
                    ×
                  </button>
                </li>
              ))}
              {tasks.length === 0 && <li className="task-history-empty">暂无历史任务</li>}
            </ul>
            <p>删除会清除进度、Diff 与撤销记录，不会回滚已应用的代码修改。</p>
          </div>
        )}
      </div>
      <button type="button" className="secondary" disabled={locked} onClick={() => choose()}>
        新建任务
      </button>
    </div>
  );
}

function activityText(event: TaskEvent) {
  if (event.data.message) return event.data.message;
  if (event.kind === 'command.completed') return `测试退出码：${event.data.exit_code ?? '超时'}`;
  if (event.kind === 'patch.proposed') return '修改已准备好，请审阅后应用。';
  if (event.kind === 'patch.applied') return '修改已应用。';
  if (event.kind === 'patch.reverted') return '修改已撤销。';
  if (event.kind === 'patch.rejected') return '本次修改已拒绝。';
  if (event.kind === 'agent.step') return `正在处理第 ${event.data.step || 0} 步`;
  if (event.kind.startsWith('task.')) return statusLabels[event.kind.slice(5)] || '任务状态已更新';
  return event.data.text || event.kind;
}

export function FeatureDialog(props: FeatureDialogProps) {
  const {
    action,
    workspace,
    selectedFile,
    settings,
    task,
    tasks,
    prompt,
    onPromptChange,
    testEnabled,
    testCommand,
    onTestsChange,
    onTestCommandChange,
    busy,
    sending,
    operationPending,
    activity,
    logs,
    error,
    onClose,
    onSettings,
    onStart,
    onLoadTask,
    onDeleteTask,
    onNewTask,
    onReview,
    onUndo,
    onCancel,
    onResumeTask,
  } = props;
  const dialog = useDialogFocus<HTMLDivElement>(onClose);
  const title = action === 'comment' ? '代码注释' : '项目解析';
  const locked = busy || sending || operationPending;
  const annotationSkill = action === 'comment' && (!task || task.skill === 'annotate-project-zh');
  const documentationSkill =
    action === 'analysis' && (!task || task.skill === 'analyze-project-zh');
  const canResume =
    task?.skill === 'annotate-project-zh' &&
    ['cancelled', 'interrupted', 'failed', 'budget_exhausted'].includes(task.status);
  const resumeBudgetReached = !!task && !!settings && task.steps >= settings.max_steps;
  const progressList = useRef<HTMLOListElement>(null);
  const followProgress = useRef(true);
  useLayoutEffect(() => {
    followProgress.current = true;
    const list = progressList.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [task?.id]);
  useLayoutEffect(() => {
    const list = progressList.current;
    if (list && followProgress.current) list.scrollTop = list.scrollHeight;
  }, [activity.length]);
  return (
    <div className="modal-shade feature-shade">
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`feature-dialog feature-${action} ${task ? 'has-task' : 'is-draft'}`}
      >
        <header className="feature-heading">
          <div>
            <span className="feature-eyebrow">CODE ASSISTANT</span>
            <h2>{title}</h2>
          </div>
          <button
            type="button"
            className="feature-close"
            aria-label="关闭任务面板"
            onClick={onClose}
          >
            ×
          </button>
        </header>
        <div className="feature-scroll">
          <div className="feature-context">
            <div className="feature-project" title={workspace.root}>
              <strong>{workspace.name}</strong>
              <span>
                {annotationSkill || documentationSkill
                  ? `${annotationSkill ? '注释' : '解析'}范围：整个项目的自有源码`
                  : selectedFile
                    ? `当前文件：${selectedFile}`
                    : '使用整个项目上下文'}
              </span>
              {annotationSkill && (
                <span role="note">
                  请求超时会持续重试，等待不消耗步数且不受任务总时限中止，可随时停止当前任务。
                </span>
              )}
              {documentationSkill && (
                <span role="note">
                  输出：项目说明.md，以及 docs/diagrams/ 中的说明、架构图、流程图和时序图（PNG）。
                </span>
              )}
              {documentationSkill && (
                <span role="note">
                  根据实际代码静态解析，不运行项目；文档包校验通过后自动接受并应用，保留 Diff、图片预览和撤销记录。
                </span>
              )}
              {annotationSkill && (
                <span role="note">
                  按 annotate-project-zh 添加文件头与逐函数注释，校验后自动应用；保留 Diff
                  和撤销记录，不运行项目。
                </span>
              )}
            </div>
            <button
              type="button"
              className="secondary model-button"
              aria-label="模型设置"
              onClick={onSettings}
            >
              {settings?.model || '连接模型'}
            </button>
          </div>
          <TaskHistory
            task={task}
            tasks={tasks}
            busy={busy}
            sending={sending}
            operationPending={operationPending}
            onLoadTask={onLoadTask}
            onNewTask={onNewTask}
            onDeleteTask={onDeleteTask}
          />
          <form
            className="feature-request"
            onSubmit={(event) => {
              event.preventDefault();
              onStart();
            }}
          >
            <label className="feature-input-label" htmlFor="feature-prompt">
              任务需求
            </label>
            <textarea
              id="feature-prompt"
              aria-label="任务需求"
              value={task?.prompt ?? prompt}
              onChange={(event) => onPromptChange(event.target.value)}
              disabled={locked || !!task}
              placeholder={
                action === 'comment' ? '补充整个项目的注释要求…' : '说明项目文档需要包含的内容…'
              }
            />
            {!task && (
              <>
                {action === 'analysis' && !documentationSkill && (
                  <>
                    <label className="feature-test-toggle">
                      <input
                        type="checkbox"
                        checked={testEnabled}
                        onChange={(event) => onTestsChange(event.target.checked)}
                        disabled={locked}
                      />
                      允许此任务运行测试
                    </label>
                    {testEnabled && (
                      <input
                        className="feature-test-command"
                        aria-label="授权测试命令"
                        value={testCommand}
                        onChange={(event) => onTestCommandChange(event.target.value)}
                        disabled={locked}
                        spellCheck={false}
                      />
                    )}
                  </>
                )}
                <div className="feature-start-row">
                  <span>
                    {settings?.model
                      ? annotationSkill
                        ? '注释校验通过后自动应用，可查看 Diff 并撤销。'
                        : documentationSkill
                          ? '文档包校验通过后自动应用，生成项目说明和三张 PNG，可撤销。'
                          : '修改将先展示，确认后写入项目。'
                      : '先连接模型，再开始处理。'}
                  </span>
                  <button
                    className="primary feature-start"
                    type="submit"
                    disabled={locked || !prompt.trim() || !settings?.model}
                  >
                    {sending ? '提交中…' : action === 'comment' ? '开始注释' : '开始解析'}
                  </button>
                </div>
              </>
            )}
          </form>
          {error && (
            <div className="error-inline" role="alert">
              {error}
            </div>
          )}
          {task && (
            <section className="feature-task" aria-label="任务进度">
              <div className="feature-section-title">
                <h3>处理进度</h3>
                <span className={`task-status ${task.status}`}>
                  {statusLabels[task.status] || task.status}
                </span>
                <span className="feature-step-count">
                  {task.steps} / {settings?.max_steps || 1000} 步
                </span>
                {busy && (
                  <button
                    type="button"
                    className="secondary cancel-task"
                    disabled={operationPending}
                    onClick={onCancel}
                  >
                    停止当前任务
                  </button>
                )}
                {canResume && (
                  <button
                    type="button"
                    className="primary resume-task"
                    disabled={locked || !settings || resumeBudgetReached}
                    onClick={onResumeTask}
                  >
                    {operationPending ? '正在恢复…' : '继续执行'}
                  </button>
                )}
              </div>
              {canResume && (
                <p className="feature-resume-hint">
                  {resumeBudgetReached
                    ? '已达到执行步数上限，请先在模型设置中提高步数，再继续执行。'
                    : '沿用此任务的历史、已用步数和已应用修改，使用当前模型配置继续处理。'}
                </p>
              )}
              {activity.length > 0 && (
                <ol
                  ref={progressList}
                  className="feature-activity"
                  aria-label="处理进度记录"
                  tabIndex={0}
                  onScroll={(event) => {
                    const list = event.currentTarget;
                    followProgress.current =
                      list.scrollHeight - list.scrollTop - list.clientHeight < 24;
                  }}
                >
                  {activity
                    .filter(
                      (event) =>
                        !['model.delta', 'command.output', 'task.queued'].includes(event.kind),
                    )
                    .map((event, index) => (
                      <li
                        key={event.id ?? `${event.kind}-${index}`}
                        className={/error|failed/.test(event.kind) ? 'activity-error' : ''}
                      >
                        {activityText(event)}
                      </li>
                    ))}
                </ol>
              )}
              {task.result && (
                <div className="feature-result" aria-label="处理结果">
                  {task.result}
                </div>
              )}
            </section>
          )}
          {task?.patches?.map((patch, patchIndex) => (
            <section
              className="patch-review"
              key={patch.id}
              aria-label={`修改审阅 ${patchIndex + 1}`}
            >
              <div className="feature-section-title">
                <h3>
                  {task.skill === 'annotate-project-zh'
                    ? '注释修改记录'
                    : task.skill === 'analyze-project-zh'
                      ? '文档修改记录'
                      : '修改审阅'} ·{' '}
                  {patch.changes.length} 个文件
                </h3>
                <span className={`patch-status ${patch.status}`}>
                  {patchLabels[patch.status] || patch.status}
                </span>
              </div>
              {patch.changes.map((change, index) => (
                <details key={change.path} className="patch-file" open={index === 0}>
                  <summary>
                    {change.path}
                    {change.encoding === 'base64' && change.mime_type === 'image/png'
                      ? ' · PNG'
                      : ''}
                    <span>
                      {change.before === null ? '新增' : change.after === null ? '删除' : '修改'}
                    </span>
                  </summary>
                  {change.encoding === 'base64' ? (
                    change.mime_type === 'image/png' ? (
                      <div className="patch-image-preview" aria-label={`${change.path} 的图片修改`}>
                        {(['before', 'after'] as const).map((side) => (
                          <figure key={side}>
                            <figcaption>{side === 'before' ? '修改前' : '修改后'}</figcaption>
                            {change[side] === null ? (
                              <p>{side === 'before' ? '原文件不存在' : '文件将被删除'}</p>
                            ) : (
                              <img
                                src={`data:image/png;base64,${change[side]}`}
                                alt={`${change.path} ${side === 'before' ? '修改前' : '修改后'} PNG 预览`}
                                loading="lazy"
                                decoding="async"
                              />
                            )}
                          </figure>
                        ))}
                      </div>
                    ) : (
                      <p className="patch-binary-note">二进制文件，当前仅支持 PNG 预览。</p>
                    )
                  ) : (
                    <pre className="patch-diff" aria-label={`${change.path} 的修改内容`}>
                      {change.diff || (change.after ?? change.before ?? '没有文本差异')}
                    </pre>
                  )}
                </details>
              ))}
              <div className="patch-actions">
                {patch.status === 'proposed' && (
                  <>
                    <button
                      type="button"
                      className="secondary"
                      disabled={operationPending || task.status !== 'waiting_review'}
                      onClick={() => onReview(patch.id, false)}
                    >
                      拒绝
                    </button>
                    <button
                      type="button"
                      className="primary"
                      disabled={operationPending || task.status !== 'waiting_review'}
                      onClick={() => onReview(patch.id, true)}
                    >
                      接受并应用
                    </button>
                  </>
                )}
                {['applied', 'recovery_required'].includes(patch.status) && (
                  <button
                    type="button"
                    className="secondary"
                    disabled={locked}
                    onClick={() => onUndo(patch.id)}
                  >
                    撤销此补丁
                  </button>
                )}
              </div>
            </section>
          ))}
          {logs && (
            <section className="feature-output" aria-label="运行输出">
              <h3>运行输出</h3>
              <pre className="terminal-output">{logs}</pre>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
