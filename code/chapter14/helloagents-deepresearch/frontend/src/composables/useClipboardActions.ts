import type { Ref } from "vue";

interface ReadonlyRef<T> {
  readonly value: T;
}

interface UseClipboardActionsOptions {
  currentTaskSourcesText: ReadonlyRef<string>;
  currentTaskTitle: ReadonlyRef<string>;
  progressLogs: Ref<string[]>;
  reportMarkdown: ReadonlyRef<string>;
}

export function useClipboardActions(options: UseClipboardActionsOptions) {
  async function copyText(
    text: string | null | undefined,
    successLog: string,
    promptTitle: string
  ) {
    if (!text) {
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      options.progressLogs.value.push(successLog);
    } catch (error) {
      console.warn("无法直接复制到剪贴板", error);
      window.prompt(promptTitle, text);
      options.progressLogs.value.push("请手动复制内容");
    }
  }

  async function copyNotePath(path: string | null | undefined) {
    if (!path) {
      return;
    }

    await copyText(path, `已复制笔记路径：${path}`, "复制以下笔记路径");
  }

  async function copyReport() {
    await copyText(
      options.reportMarkdown.value,
      "已复制找实习行动报告",
      "复制以下报告内容"
    );
  }

  async function copyCurrentTaskSources() {
    const title = options.currentTaskTitle.value || "当前任务";
    await copyText(
      options.currentTaskSourcesText.value,
      `已复制来源：${title}`,
      "复制以下来源内容"
    );
  }

  return {
    copyCurrentTaskSources,
    copyNotePath,
    copyReport,
    copyText
  };
}
