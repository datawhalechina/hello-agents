import { useEffect, useState } from 'react';
import type { DragEvent } from 'react';
import type { Workspace } from './types';

export type HomeAction = 'comment' | 'analysis';

export function Butterfly({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <defs>
        <linearGradient
          id="butterfly-wing"
          x1="10"
          y1="3"
          x2="49"
          y2="57"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#f4ffff" />
          <stop offset=".4" stopColor="#55d7ff" />
          <stop offset=".7" stopColor="#3b80ff" />
          <stop offset="1" stopColor="#d2faff" />
        </linearGradient>
      </defs>
      <path
        d="M30 31C21 8 2-2 7 19c3 11 13 15 23 14ZM34 31C43 8 62-2 57 19c-3 11-13 15-23 14ZM29 35C13 29 5 39 11 51c5 9 16-4 19-14ZM35 35c16-6 24 4 18 16-5 9-16-4-19-14Z"
        fill="url(#butterfly-wing)"
        stroke="#b8f5ff"
        strokeWidth="1.4"
      />
      <path
        d="M11 13 27 29 15 24m38-11L37 29l12-5M15 45l13-9m21 9-13-9"
        stroke="#e2ffff"
        strokeWidth="1.7"
      />
      <path d="m28 23 4 8 4-8m-4 8v16" stroke="#f4ffff" strokeWidth="2" strokeLinecap="round" />
      <path d="m12 55 1-4m38 4-1-4" stroke="#d4faff" strokeWidth="2" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg viewBox="0 0 160 150" fill="none" aria-hidden="true">
      <path
        d="M17 43V33c0-10 7-17 17-17h31c8 0 10 5 18 14h43c11 0 18 7 18 18v77c0 10-7 17-17 17H34c-10 0-17-7-17-17V43Z"
        fill="#1c65db"
        fillOpacity=".4"
        stroke="#78dcff"
        strokeWidth="8"
      />
      <path
        d="M17 43V33c0-10 7-17 17-17h31c8 0 10 5 18 14h43c11 0 18 7 18 18v77c0 10-7 17-17 17H34c-10 0-17-7-17-17V43Z"
        stroke="white"
        strokeWidth="3.5"
      />
      <path
        d="M73 62h15v29h16l-24 24-24-24h17V62Z"
        fill="#a3edff"
        stroke="white"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DocumentIcon({ code = false }: { code?: boolean }) {
  return (
    <svg viewBox="0 0 100 110" fill="none" aria-hidden="true">
      <path
        d="M66 10H23c-5 0-8 3-8 8v76c0 5 3 8 8 8h59c5 0 8-3 8-8V35L66 10Zm0 0v25h24"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinejoin="round"
      />
      {code ? (
        <>
          <path
            d="m38 52-12 11 12 11m27-22 12 11-12 11M57 48 46 79"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="m58 93 28-30 10 10-28 30-13 4 3-14Zm23-25 10 10"
            fill="#126bdf"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinejoin="round"
          />
        </>
      ) : (
        <path
          d="M31 51h40M31 66h40M31 81h28"
          stroke="currentColor"
          strokeWidth="5"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}

function ReadyProjectArt() {
  return (
    <span className="project-ready-art" aria-hidden="true">
      <span className="project-ripple" />
      <span className="project-ripple project-ripple-outer" />
      <Butterfly className="project-butterfly project-butterfly-left" />
      <Butterfly className="project-butterfly project-butterfly-right" />
      <i className="magic-star project-spark project-spark-left" />
      <i className="magic-star project-spark project-spark-right" />
      <svg className="ready-folder" viewBox="0 0 200 160" fill="none">
        <defs>
          <linearGradient
            id="ready-folder-fill"
            x1="36"
            y1="62"
            x2="163"
            y2="153"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#7eeaff" />
            <stop offset=".45" stopColor="#2798f5" />
            <stop offset="1" stopColor="#1c4bc2" />
          </linearGradient>
          <linearGradient
            id="ready-paper-fill"
            x1="102"
            y1="10"
            x2="145"
            y2="104"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#fff" />
            <stop offset="1" stopColor="#9bd7ff" />
          </linearGradient>
        </defs>
        <path
          d="M24 57c0-7 5-12 12-12h39l14 12h69c8 0 13 6 12 13l-9 65H34L24 57Z"
          fill="#1557bd"
          stroke="#85dcff"
          strokeWidth="2"
        />
        <g className="ready-folder-papers">
          <path
            d="m99 10 66 10c5 1 8 5 7 10l-12 83-80-12 12-83c1-5 3-9 7-8Z"
            fill="url(#ready-paper-fill)"
            stroke="#e9fcff"
            strokeWidth="2"
          />
          <path
            d="m110 32 43 7m-47 10 43 7m-46 10 36 6"
            stroke="#71a9e8"
            strokeWidth="4"
            strokeLinecap="round"
          />
          <path
            d="m66 24 57 12c5 1 7 5 6 10l-15 72-73-15 16-72c1-5 4-8 9-7Z"
            fill="#133a80"
            stroke="#96ddff"
            strokeWidth="2"
          />
          <path
            d="m77 52-12 9 8 13m24-18 8 13-12 9m-5-26-8 28"
            stroke="#96edff"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
        <path
          d="M26 66c-1-7 4-12 11-11l35 6 10 16 78 15c7 1 11 7 9 14l-9 35c-1 6-6 9-12 8L45 130c-5-1-9-5-10-11L26 66Z"
          fill="url(#ready-folder-fill)"
          stroke="#bbf8ff"
          strokeWidth="2.5"
        />
        <path
          d="m42 69 26 5 10 15 71 13"
          stroke="#c7ffff"
          strokeOpacity=".6"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      <span className="project-success-badge">
        <svg viewBox="0 0 32 32">
          <path
            d="m8 16 6 6L25 10"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
    </span>
  );
}

export function ClientTitlebar({
  canResume,
  onResume,
  onSettings,
  settingsReady,
  report,
}: {
  canResume: boolean;
  onResume: () => void;
  onSettings: () => void;
  settingsReady: boolean;
  report: (error: unknown) => void;
}) {
  const [maximized, setMaximized] = useState(false);
  useEffect(() => {
    document.documentElement.classList.toggle('is-maximized', maximized);
    return () => document.documentElement.classList.remove('is-maximized');
  }, [maximized]);
  useEffect(() => {
    let active = true;
    const sync = () => {
      if (!window.codeAssistant) return;
      void window.codeAssistant
        .windowState()
        .then((state) => {
          if (active) setMaximized(state.maximized);
        })
        .catch(report);
    };
    sync();
    window.addEventListener('resize', sync);
    return () => {
      active = false;
      window.removeEventListener('resize', sync);
    };
  }, [report]);
  async function control(action: 'minimize' | 'maximize' | 'close') {
    try {
      const state = await window.codeAssistant.windowControl(action);
      setMaximized(state.maximized);
    } catch (error) {
      report(error);
    }
  }
  return (
    <header className="client-titlebar">
      <div className="client-brand">
        <Butterfly className="client-logo" />
        <strong>代码助手</strong>
        <span>CodeAssistantAgent</span>
      </div>
      <div className="client-toolbar">
        {canResume && (
          <button className="task-resume" onClick={onResume}>
            继续任务
          </button>
        )}
        <button
          className="client-settings"
          aria-label="模型设置"
          title="模型设置"
          disabled={!settingsReady}
          onClick={onSettings}
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="m10 3-.6 2.1-2 .9-2-.6L3.5 8l1.5 1.6v2.8L3.5 14l1.9 2.6 2-.6 2 .9L10 19h3l.6-2.1 2-.9 2 .6 1.9-2.6-1.5-1.6V9.6L19.5 8l-1.9-2.6-2 .6-2-.9L13 3h-3Z"
              stroke="currentColor"
              strokeWidth="1.3"
              strokeLinejoin="round"
            />
            <circle cx="11.5" cy="11" r="3" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        </button>
      </div>
      <div className="window-controls">
        <button aria-label="最小化" onClick={() => void control('minimize')}>
          <svg viewBox="0 0 20 20">
            <path d="M3 10h14" />
          </svg>
        </button>
        <button aria-label="最大化或还原" onClick={() => void control('maximize')}>
          <svg viewBox="0 0 20 20">
            {maximized ? <path d="M6 6V3h11v11h-3M3 6h11v11H3Z" /> : <path d="M3 3h14v14H3Z" />}
          </svg>
        </button>
        <button
          className="window-close"
          aria-label="关闭窗口"
          onClick={() => void control('close')}
        >
          <svg viewBox="0 0 20 20">
            <path d="m4 4 12 12M16 4 4 16" />
          </svg>
        </button>
      </div>
    </header>
  );
}

export function ClientHome({
  workspace,
  booting,
  importing,
  importRevision,
  selectedFile,
  clearDisabled,
  onClear,
  onChoose,
  onDrop,
  onAction,
}: {
  workspace: Workspace | null;
  booting: boolean;
  importing: boolean;
  importRevision: number;
  selectedFile: string | null;
  clearDisabled: boolean;
  onClear: () => void;
  onChoose: () => void;
  onDrop: (file: File) => void;
  onAction: (action: HomeAction) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const [celebrating, setCelebrating] = useState(false);
  const ready = !!workspace && !booting && !importing;
  useEffect(() => {
    setCelebrating(false);
    if (!importRevision) return;
    setCelebrating(true);
    const timeout = window.setTimeout(() => setCelebrating(false), 2200);
    return () => window.clearTimeout(timeout);
  }, [importRevision]);
  useEffect(() => {
    if (importing) setCelebrating(false);
  }, [importing]);
  function drop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    if (booting || importing) return;
    const file = event.dataTransfer.files[0];
    if (file) onDrop(file);
  }
  return (
    <main className="home-content" aria-label="代码助手首页">
      <div
        className={`home-grid ${ready ? 'has-project' : ''} ${celebrating && ready ? 'is-celebrating' : ''}`}
      >
        <div className="project-drop-panel">
          <button
            className={`project-drop ${dragging ? 'is-dragging' : ''} ${ready ? 'is-ready' : ''} ${importing ? 'is-importing' : ''}`}
            aria-label="导入项目"
            aria-busy={booting || importing}
            title={
              workspace ? `${workspace.root}\n点击更换项目，或拖入新的文件夹或代码文件` : undefined
            }
            disabled={booting || importing}
            onClick={onChoose}
            onDragOver={(event) => {
              event.preventDefault();
              event.dataTransfer.dropEffect = 'copy';
              if (!booting && !importing) setDragging(true);
            }}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget as Node | null))
                setDragging(false);
            }}
            onDrop={drop}
          >
            <span className="drop-interior" key={importRevision}>
              {ready ? (
                <ReadyProjectArt />
              ) : (
                <span className="folder-illustration" aria-hidden="true">
                  <i className="magic-star" />
                  <FolderIcon />
                  <i className="magic-star" />
                  {importing && <span className="import-spinner" />}
                </span>
              )}
              <strong role="status">
                {booting
                  ? '正在连接本地服务'
                  : importing
                    ? '正在导入项目…'
                    : dragging
                      ? '松开以导入项目'
                      : ready
                        ? '项目已就绪'
                        : '将项目拖入这里'}
              </strong>
              {ready && workspace ? (
                <>
                  <span className="selected-project" title={workspace.root}>
                    <span className="project-name-icon" aria-hidden="true">
                      <FolderIcon />
                    </span>
                    <span className="project-name">{workspace.name}</span>
                  </span>
                  <span className="drop-description" title={selectedFile || undefined}>
                    {selectedFile ? '已导入代码文件' : '已导入项目文件夹'}
                  </span>
                  <span className="project-ready-hint">可开始代码注释或项目解析</span>
                  <span className="project-replace-hint">点击或拖入以更换项目</span>
                </>
              ) : (
                <span className="drop-description">拖入整个项目文件夹或代码文件</span>
              )}
            </span>
          </button>
          {workspace && !booting && (
            <button
              type="button"
              className="project-clear"
              aria-label="清除当前项目"
              title={clearDisabled ? '请先结束当前操作，再清除项目' : '清除当前项目（不删除文件）'}
              disabled={clearDisabled || importing}
              onClick={onClear}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="m7 7 10 10M17 7 7 17" />
              </svg>
            </button>
          )}
        </div>
        <div className="home-actions">
          <button
            className="home-action home-action-comment"
            onClick={() => onAction('comment')}
            disabled={booting || importing}
          >
            <span className="action-icon">
              <DocumentIcon code />
            </span>
            <span className="action-copy">
              <strong>代码注释</strong>
              <span>
                为项目代码
                <br />
                生成中文注释
              </span>
            </span>
            <Butterfly className="card-butterfly" />
            <span className="card-orbit" aria-hidden="true" />
          </button>
          <button
            className="home-action home-action-analysis"
            onClick={() => onAction('analysis')}
            disabled={booting || importing}
          >
            <span className="action-icon">
              <DocumentIcon />
            </span>
            <span className="action-copy">
              <strong>项目解析</strong>
              <span>生成项目说明文档</span>
            </span>
            <span className="gold-star" aria-hidden="true">
              ✧
            </span>
            <span className="card-orbit" aria-hidden="true" />
          </button>
        </div>
      </div>
    </main>
  );
}
