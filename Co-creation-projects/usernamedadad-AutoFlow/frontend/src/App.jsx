import { useEffect, useMemo, useRef, useState } from "react";
import { buildPlan, streamAgentChat } from "./services/api";
import { renderMermaid } from "./services/mermaid";

const MODES = [
  { key: "inspire", label: "灵感模式" },
  { key: "standard", label: "标准模式" },
  { key: "plan", label: "计划模式" },
  { key: "code", label: "Mermaid 代码模式" },
];

const DIRECTION_OPTIONS = [
  { key: "TD", label: "上到下" },
  { key: "LR", label: "左到右" },
];

const MODE_PLACEHOLDER = {
  plan: "按行输入流程步骤，例如:\n开始\n数据清洗\n模型训练\n结束",
  code: "直接输入 Mermaid 代码",
  standard: "请开始输入...",
  inspire: "请开始输入...",
};

const CHAT_EMPTY_TEXT = {
  standard: "告诉我你的需求，我来帮你优化提示词并生成流程图。",
  inspire: "告诉我你的灵感或想法，我来帮你完善并生成流程图。",
};

const ASSISTANT_PREFIX = {
  standard: "根据你的需求生成的流程图代码：",
  inspire: "根据你的灵感生成的流程图代码：",
};

function downloadText(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [mode, setMode] = useState("plan");
  const [direction, setDirection] = useState("TD");
  const [input, setInput] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [mermaidCode, setMermaidCode] = useState("flowchart TD\n    A[AutoFlow] --> B[就绪]");
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");
  const [statusText, setStatusText] = useState("等待生成");
  const [loading, setLoading] = useState(false);
  const [chatMap, setChatMap] = useState({ standard: [], inspire: [] });
  const [thinkingMap, setThinkingMap] = useState({ standard: false, inspire: false });
  const [zoom, setZoom] = useState(1);
  const previewRef = useRef(null);
  const dragStateRef = useRef({ dragging: false, startX: 0, startY: 0, startLeft: 0, startTop: 0 });

  const isChatMode = mode === "standard" || mode === "inspire";

  const currentChat = chatMap[mode] || [];
  const isThinking = thinkingMap[mode] || false;

  const pushChatMessage = (targetMode, message) => {
    setChatMap((prev) => ({
      ...prev,
      [targetMode]: [...(prev[targetMode] || []), message],
    }));
  };

  const canGenerate = useMemo(() => {
    if (isChatMode) return chatInput.trim().length > 0;
    if (mode === "code") return mermaidCode.trim().length > 0;
    return input.trim().length > 0;
  }, [mode, input, mermaidCode, chatInput, isChatMode]);

  const applyDirectionToCode = (code, targetDirection) => {
    const raw = (code || "").trim();
    if (!raw) return "";

    const normalized = targetDirection === "LR" ? "LR" : "TD";
    const lines = raw.split("\n");
    const firstIdx = lines.findIndex((line) => line.trim().length > 0);
    if (firstIdx === -1) return raw;

    const firstLine = lines[firstIdx];
    if (/^(flowchart|graph)\s+(TD|LR|TB|BT|RL)\b/i.test(firstLine.trim())) {
      lines[firstIdx] = firstLine.replace(/^(\s*)(flowchart|graph)\s+(TD|LR|TB|BT|RL)\b/i, `$1$2 ${normalized}`);
      return lines.join("\n");
    }

    if (/^(flowchart|graph)\b/i.test(firstLine.trim())) {
      lines[firstIdx] = firstLine.replace(/^(\s*)(flowchart|graph)\b/i, `$1$2 ${normalized}`);
      return lines.join("\n");
    }

    return `flowchart ${normalized}\n${raw}`;
  };

  const previewMermaidCode = useMemo(() => applyDirectionToCode(mermaidCode, direction), [mermaidCode, direction]);

  const zoomLabel = `${Math.round(zoom * 100)}%`;

  const clampZoom = (value) => Math.min(3, Math.max(0.3, value));

  const zoomIn = () => setZoom((prev) => clampZoom(prev + 0.1));

  const zoomOut = () => setZoom((prev) => clampZoom(prev - 0.1));

  const resetZoom = () => setZoom(1);

  const fitToView = () => {
    if (!previewRef.current || !svg) return;
    const container = previewRef.current;
    const svgEl = container.querySelector("svg");
    if (!svgEl) return;

    const vb = svgEl.viewBox?.baseVal;
    const svgWidth = vb && vb.width ? vb.width : svgEl.getBoundingClientRect().width;
    const svgHeight = vb && vb.height ? vb.height : svgEl.getBoundingClientRect().height;
    if (!svgWidth || !svgHeight) return;

    const innerPadding = 32;
    const availableWidth = Math.max(120, container.clientWidth - innerPadding);
    const availableHeight = Math.max(120, container.clientHeight - innerPadding);
    const fitted = clampZoom(Math.min(availableWidth / svgWidth, availableHeight / svgHeight));

    setZoom(fitted);
    container.scrollLeft = 0;
    container.scrollTop = 0;
  };

  const handlePreviewMouseDown = (e) => {
    if (!svg || !previewRef.current) return;
    const container = previewRef.current;
    dragStateRef.current = {
      dragging: true,
      startX: e.clientX,
      startY: e.clientY,
      startLeft: container.scrollLeft,
      startTop: container.scrollTop,
    };
  };

  const handlePreviewMouseMove = (e) => {
    if (!previewRef.current) return;
    const drag = dragStateRef.current;
    if (!drag.dragging) return;
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    previewRef.current.scrollLeft = drag.startLeft - dx;
    previewRef.current.scrollTop = drag.startTop - dy;
  };

  const stopPreviewDrag = () => {
    dragStateRef.current.dragging = false;
  };

  useEffect(() => {
    async function draw() {
      const code = (previewMermaidCode || "").trim();
      if (!code) {
        setSvg("");
        setError("");
        return;
      }

      try {
        const result = await renderMermaid(code);
        setSvg(result.svg);
        setError("");
      } catch (e) {
        setError(`渲染错误: ${e.message}`);
      }
    }
    draw();
  }, [previewMermaidCode]);

  const runPlanMode = async () => {
    const data = await buildPlan(input, "TD");
    setMermaidCode(data.mermaid_code || "");
    setZoom(1);
    setStatusText("计划模式: 已生成流程图，可在预览区切换方向");
  };

  const runCodeMode = async () => {
    setStatusText("代码模式: 使用当前编辑器代码渲染");
  };

  const runAgentMode = async () => {
    const modeKey = mode === "inspire" ? "inspire" : "standard";
    const userPrompt = chatInput.trim();

    if (!userPrompt) return;

    pushChatMessage(modeKey, { role: "user", content: userPrompt, kind: "text" });
    setThinkingMap((prev) => ({ ...prev, [modeKey]: true }));
    setChatInput("");
    let settled = false;

    try {
      await streamAgentChat(
        {
          mode: modeKey,
          prompt: userPrompt,
          direction: "TD",
        },
        ({ data }) => {
          if (data.type === "status") {
            setStatusText(`${data.phase}: ${data.message}`);
          }

          if (data.type === "result") {
            settled = true;
            setMermaidCode(data.mermaid_code || "");
            setZoom(1);
            setStatusText(`完成: valid=${data.valid}, attempts=${data.attempts}`);
            if (modeKey === "standard" && data.optimized_text) {
              pushChatMessage(modeKey, {
                role: "assistant",
                content: data.optimized_text,
                kind: "text",
                title: "优化后的提示词：",
              });
            }
            pushChatMessage(modeKey, {
              role: "assistant",
              content: data.mermaid_code || "",
              kind: "code",
              title: ASSISTANT_PREFIX[modeKey],
            });
          }

          if (data.type === "error") {
            settled = true;
            setError(data.message || "智能体执行失败");
          }
        }
      );

      if (!settled) {
        throw new Error("服务响应中断，请重试");
      }
    } finally {
      setThinkingMap((prev) => ({ ...prev, [modeKey]: false }));
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    setStatusText("请求处理中...");

    try {
      if (mode === "plan") {
        await runPlanMode();
      } else if (mode === "code") {
        await runCodeMode();
      } else {
        await runAgentMode();
      }
    } catch (e) {
      setError(e.message || "请求失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="topbar">
        <h1>AutoFlow</h1>
        <p>计划到流程图，一键生成与实时预览</p>
      </header>

      <main className="workspace">
        <section className="left-panel">
          <div className="tabs">
            {MODES.map((item) => (
              <button
                key={item.key}
                className={item.key === mode ? "tab active" : "tab"}
                onClick={() => setMode(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>

          {isChatMode ? (
            <>
              <div className="chat-box">
                {currentChat.length === 0 && !isThinking ? (
                  <div className="chat-empty-wrap">
                    <div className="chat-empty">{CHAT_EMPTY_TEXT[mode]}</div>
                    {mode === "inspire" ? <div className="chat-empty-sub">例如："我想开发一个电商平台"。</div> : null}
                  </div>
                ) : (
                  currentChat.map((msg, idx) => (
                    <div key={`${msg.role}-${idx}`} className={`chat-msg ${msg.role}`}>
                      {msg.role === "assistant" && msg.title ? <div className="chat-title">{msg.title}</div> : null}
                      {msg.kind === "code" ? (
                        <pre className="chat-code">{msg.content}</pre>
                      ) : (
                        <p>{msg.content}</p>
                      )}
                    </div>
                  ))
                )}

                {isThinking ? (
                  <div className="chat-msg assistant thinking">
                    <div className="thinking-bubble">
                      正在思考
                      <span className="dots">...</span>
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="chat-input-row">
                <textarea
                  className="chat-input"
                  placeholder={MODE_PLACEHOLDER[mode]}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !loading) {
                      handleGenerate();
                    }
                  }}
                  rows={3}
                />
                <button className="primary" disabled={!canGenerate || loading} onClick={handleGenerate}>
                  {loading ? "生成中" : "发送"}
                </button>
              </div>
            </>
          ) : (
            <>
              <textarea
                className="editor"
                placeholder={MODE_PLACEHOLDER[mode]}
                value={mode === "code" ? mermaidCode : input}
                onChange={(e) => {
                  if (mode === "code") {
                    setMermaidCode(e.target.value);
                  } else {
                    setInput(e.target.value);
                  }
                }}
              />

              <div className="actions">
                <button className="primary" disabled={!canGenerate || loading} onClick={handleGenerate}>
                  {loading ? "生成中..." : "生成/更新"}
                </button>
              </div>
            </>
          )}

          <div className="log-box">
            <strong>当前状态</strong>
            {loading && <div className="loader" aria-label="loading" />}
            <p>{statusText}</p>
          </div>
        </section>

        <section className="right-panel">
          <div className="panel-header">
            <h2>实时预览</h2>
            <div className="panel-tools">
              <div className="preview-controls">
                <button className="ghost" onClick={zoomOut} disabled={!svg}>
                  缩小
                </button>
                <span className="zoom-label">{zoomLabel}</span>
                <button className="ghost" onClick={zoomIn} disabled={!svg}>
                  放大
                </button>
                <button className="ghost" onClick={resetZoom} disabled={!svg}>
                  100%
                </button>
                <button className="ghost" onClick={fitToView} disabled={!svg}>
                  适应窗口
                </button>
              </div>
              <div className="direction-switch">
                {DIRECTION_OPTIONS.map((item) => (
                  <button
                    key={item.key}
                    className={item.key === direction ? "dir-btn active" : "dir-btn"}
                    onClick={() => setDirection(item.key)}
                    disabled={!svg}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <div className="export-actions">
              <button className="ghost" onClick={() => downloadText("autoflow.mmd", previewMermaidCode)}>
                导出 .mmd
              </button>
              <button className="ghost" onClick={() => downloadText("autoflow.svg", svg)} disabled={!svg}>
                导出 SVG
              </button>
              </div>
            </div>
          </div>
          {error && (mermaidCode || "").trim() ? <div className="error">{error}</div> : null}
          <div
            className={svg ? "preview" : "preview is-empty"}
            ref={previewRef}
            onMouseDown={handlePreviewMouseDown}
            onMouseMove={handlePreviewMouseMove}
            onMouseUp={stopPreviewDrag}
            onMouseLeave={stopPreviewDrag}
          >
            {svg ? (
              <div className="preview-scale" style={{ transform: `scale(${zoom})` }}>
                <div className="preview-inner" dangerouslySetInnerHTML={{ __html: svg }} />
              </div>
            ) : (
              <div className="preview-empty">暂无图表...</div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
