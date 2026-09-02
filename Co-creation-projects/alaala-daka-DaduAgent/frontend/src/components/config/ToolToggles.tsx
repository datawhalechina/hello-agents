import React from 'react';
import { Toggle } from '../shared/Toggle';

const TOOLS = [
  { name: 'search', label: '网络搜索', desc: 'Tavily 实时搜索' },
  { name: 'calculator', label: '计算器', desc: '安全数学表达式求值' },
  { name: 'todo', label: '待办清单', desc: '任务规划与追踪' },
  { name: 'reflection', label: '反思笔记', desc: '经验沉淀与回顾' },
  { name: 'rag_summarize', label: '知识库检索', desc: '本地 RAG 搜索' },
  { name: 'file_manage', label: '文件管理', desc: 'CRUD 文件操作' },
  { name: 'ask_for_answer', label: '用户确认', desc: '需求澄清提问' },
  { name: 'session', label: '会话管理', desc: '会话 CRUD' },
];

export const ToolToggles: React.FC = () => (
  <div className="space-y-3">
    <p className="text-[11px] text-[#AEAEB2] font-sidebar">
      工具开关仅在下次创建 Agent 时生效
    </p>
    {TOOLS.map((tool) => (
      <div key={tool.name} className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-medium text-[#1D1D1F] font-sidebar">{tool.label}</div>
          <div className="text-[11px] text-[#AEAEB2] font-sidebar truncate">{tool.desc}</div>
        </div>
        <Toggle checked={true} onChange={() => {}} disabled />
      </div>
    ))}
  </div>
);
