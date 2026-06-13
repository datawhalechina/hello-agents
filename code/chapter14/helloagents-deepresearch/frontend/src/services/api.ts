const baseURL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface ResearchRequest {
  topic: string;
  search_api?: string;
}

export interface ResearchStreamEvent {
  type: string;
  [key: string]: unknown;
}

export interface StreamOptions {
  signal?: AbortSignal;
}

export class StreamInterruptedError extends Error {
  constructor(message = "找实习连接中断，尚未收到完成信号") {
    super(message);
    this.name = "StreamInterruptedError";
  }
}

export interface JobApplicationPayload {
  id?: string | null;
  company: string;
  title: string;
  location: string;
  source_url: string;
  source_title: string;
  requirements: string[];
  responsibilities: string[];
  tech_stack: string[];
  duration: string;
  deadline: string;
  match_score: number | null;
  match_reason: string;
  resume_advice: string[];
  risks: string[];
  application_status?: string | null;
  status_note?: string | null;
  application_channel?: string | null;
  applied_at?: string | null;
  next_action?: string | null;
  next_action_at?: string | null;
  resume_version?: string | null;
  withdrawal_reason?: string | null;
}

export type JobApplicationTrackingField =
  | "application_channel"
  | "applied_at"
  | "next_action"
  | "next_action_at"
  | "resume_version"
  | "withdrawal_reason";

export type JobApplicationUpdatePayload = Partial<
  Pick<
    JobApplicationPayload,
    | "application_status"
    | "status_note"
    | JobApplicationTrackingField
  >
>;

export interface ApplicationListResponse {
  job_items: unknown[];
  statuses: string[];
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${baseURL}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(errorText || `请求失败，状态码：${response.status}`);
  }

  return (await response.json()) as T;
}

export async function listApplications(): Promise<ApplicationListResponse> {
  return requestJson<ApplicationListResponse>("/applications");
}

export async function saveApplication(
  payload: JobApplicationPayload
): Promise<unknown> {
  return requestJson<unknown>("/applications", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateApplication(
  id: string,
  payload: JobApplicationUpdatePayload
): Promise<unknown> {
  return requestJson<unknown>(`/applications/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteApplication(id: string): Promise<unknown> {
  return requestJson<unknown>(`/applications/${encodeURIComponent(id)}`, {
    method: "DELETE"
  });
}

export async function runResearchStream(
  payload: ResearchRequest,
  onEvent: (event: ResearchStreamEvent) => void,
  options: StreamOptions = {}
): Promise<void> {
  const response = await fetch(`${baseURL}/research/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream"
    },
    body: JSON.stringify(payload),
    signal: options.signal
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(
      errorText || `找实习请求失败，状态码：${response.status}`
    );
  }

  const body = response.body;
  if (!body) {
    throw new Error("浏览器不支持流式响应，无法获取找实习进度");
  }

  const reader = body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let receivedTerminalEvent = false;

  const handleRawEvent = (rawEvent: string): boolean => {
    if (!rawEvent.startsWith("data:")) {
      return false;
    }

    const dataPayload = rawEvent.slice(5).trim();
    if (!dataPayload) {
      return false;
    }

    try {
      const event = JSON.parse(dataPayload) as ResearchStreamEvent;
      onEvent(event);

      if (event.type === "error" || event.type === "done") {
        receivedTerminalEvent = true;
        return true;
      }
    } catch (error) {
      console.error("解析流式事件失败：", error, dataPayload);
    }

    return false;
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);

      if (handleRawEvent(rawEvent)) {
        return;
      }

      boundary = buffer.indexOf("\n\n");
    }

    if (done) {
      // 处理可能的尾巴事件
      if (buffer.trim()) {
        if (handleRawEvent(buffer.trim())) {
          return;
        }
      }
      break;
    }
  }

  if (!receivedTerminalEvent) {
    throw new StreamInterruptedError();
  }
}
