import React, { useState, useEffect } from 'react';

/** 与 Claude Code 类似的动态 ✻ 星形图标字符（循环切换） */
const GLYPHS = ['✻', '✽', '✶', '✳', '✢', '✣'];

/**
 * Agent 工作中指示器。
 * 用户等待 Agent 输出时显示在聊天区（左对齐，与 Agent 气泡同侧），
 * 通过字符循环让 ✻ 保持动态；Agent 输出结束（组件卸载）后动画随之停止。
 */
export const AgentWorkingIndicator: React.FC = () => {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setIdx((v) => (v + 1) % GLYPHS.length), 140);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex items-center gap-2 select-none pl-1">
      <span className="w-4 text-center text-[#0066CC] text-sm leading-none">
        {GLYPHS[idx]}
      </span>
      <span className="text-xs text-[#6E6E73] font-sidebar">
        Agent正在努力工作中！
      </span>
    </div>
  );
};
