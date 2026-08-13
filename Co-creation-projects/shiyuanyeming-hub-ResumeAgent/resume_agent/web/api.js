export class ApiError extends Error {
  constructor(status, category, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.category = category;
  }
}

const ERROR_COPY = {
  unavailable: "导师服务暂不可用",
  conflict: "档案已在其他位置更新，请刷新后重试",
  validation: "请检查填写内容",
  "not-found": "请求的内容已经不存在",
  "invalid-output": "导师返回的内容没有通过事实校验",
  request: "操作没有完成，请稍后重试",
  transport: "无法连接 ResumeAgent 服务",
};

function errorCategory(status) {
  if (status === 503) return "unavailable";
  if (status === 409) return "conflict";
  if (status === 422) return "validation";
  if (status === 404) return "not-found";
  if (status === 502) return "invalid-output";
  return "request";
}

export function sanitizeUiState(value) {
  const source = value && typeof value === "object" ? value : {};
  const result = {};
  for (const key of [
    "factBaseId",
    "experienceId",
    "sessionId",
    "versionId",
    "locale",
    "tab",
  ]) {
    if (typeof source[key] === "string" && source[key]) {
      result[key] = source[key];
    }
  }
  if (result.locale && !["zh", "ja", "en"].includes(result.locale)) {
    delete result.locale;
  }
  if (result.tab && !["chat", "facts", "jd", "tools"].includes(result.tab)) {
    delete result.tab;
  }
  return result;
}

export function createApi(fetchImpl = globalThis.fetch) {
  async function request(path, init = {}) {
    let response;
    try {
      response = await fetchImpl(path, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(init.headers || {}),
        },
      });
    } catch (error) {
      throw new ApiError(0, "transport", ERROR_COPY.transport);
    }
    if (!response.ok) {
      const category = errorCategory(response.status);
      throw new ApiError(response.status, category, ERROR_COPY[category]);
    }
    return response.status === 204 ? null : response.json();
  }

  return {
    health: () => request("/health"),
    capabilities: () => request("/capabilities"),
    listFactBases: () => request("/fact-bases"),
    createFactBase: (target) => request("/fact-bases", {
      method: "POST",
      body: JSON.stringify({ target }),
    }),
    addExperience: (factBaseId, payload) => request(
      `/fact-bases/${factBaseId}/experiences`,
      { method: "POST", body: JSON.stringify(payload) },
    ),
  };
}
