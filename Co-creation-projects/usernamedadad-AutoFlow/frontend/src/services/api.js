const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function buildPlan(text, direction = "TD") {
  const resp = await fetch(`${API_BASE}/api/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, direction }),
  });

  if (!resp.ok) {
    throw new Error(`计划模式请求失败: ${resp.status}`);
  }

  return resp.json();
}

function parseSSEChunk(buffer, onEvent) {
  const parts = buffer.split("\n\n");
  const remaining = parts.pop() || "";

  for (const block of parts) {
    const lines = block.split("\n");
    let eventType = "message";
    let dataLine = "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim();
      }
      if (line.startsWith("data:")) {
        dataLine += line.slice(5).trim();
      }
    }

    if (dataLine) {
      try {
        const parsed = JSON.parse(dataLine);
        onEvent({ eventType, data: parsed });
      } catch {
        onEvent({ eventType, data: { type: "error", message: "SSE 解析失败" } });
      }
    }
  }

  return remaining;
}

export async function streamAgentChat(payload, onEvent) {
  const resp = await fetch(`${API_BASE}/api/agent/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`智能体流式请求失败: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = parseSSEChunk(buffer, onEvent);
  }
}
