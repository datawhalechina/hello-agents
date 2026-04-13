import mermaid from "mermaid";

let initialized = false;

export function initMermaid() {
  if (initialized) return;
  mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    securityLevel: "loose",
    flowchart: {
      curve: "basis",
      htmlLabels: true,
      useMaxWidth: false,
    },
    themeVariables: {
      primaryColor: "#dbeafe",
      primaryBorderColor: "#2563eb",
      lineColor: "#1f2937",
      fontFamily: "IBM Plex Sans",
      textColor: "#0f172a",
    },
  });
  initialized = true;
}

export async function renderMermaid(code) {
  initMermaid();
  const id = `m-${Date.now()}`;
  return mermaid.render(id, code);
}
