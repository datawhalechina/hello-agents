import React, { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronRight } from 'lucide-react';
import { useConfig } from '../../hooks/useConfig';
import { ModelSettings } from '../config/ModelSettings';
import { ToolToggles } from '../config/ToolToggles';
import { FileModeSettings } from '../config/FileModeSettings';
import { SystemPrompt } from '../config/SystemPrompt';
import { RagSettings } from '../config/RagSettings';
import { ReflectionSettings } from '../config/ReflectionSettings';
import { Button } from '../shared/Button';

interface ConfigPanelProps {
  onClose: () => void;
}

export const ConfigPanel: React.FC<ConfigPanelProps> = ({ onClose }) => {
  const [activeSection, setActiveSection] = useState<string | null>('model');
  const [saved, setSaved] = useState(false);

  const sections = [
    { id: 'model', label: '模型设置' },
    { id: 'tools', label: '工具管理' },
    { id: 'filemode', label: '文件管理' },
    { id: 'rag', label: 'RAG 知识库' },
    { id: 'reflection', label: '反思笔记' },
    { id: 'prompt', label: '系统提示词' },
  ];

  const isReflection = activeSection === 'reflection';

  const toggleSection = (id: string) => {
    setActiveSection(prev => prev === id ? null : id);
  };

  return (
    <aside className={`${isReflection ? 'w-[520px]' : 'w-[360px]'} flex-shrink-0 glass border-l border-[#E5E5EA] animate-slide-in-right
      flex flex-col overflow-hidden transition-all duration-300`}>
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 border-b border-[#E5E5EA]">
        <h2 className="text-base font-semibold text-[#1D1D1F] font-sidebar">设置</h2>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-[#E5E5EA] transition-colors text-[#6E6E73]"
        >
          <X size={18} />
        </button>
      </div>

      {/* 分段内容 */}
      <div className="flex-1 overflow-y-auto">
        {sections.map(({ id, label }) => (
          <div key={id} className="border-b border-[#E5E5EA]">
            <button
              onClick={() => toggleSection(id)}
              className="flex items-center justify-between w-full px-4 py-3 text-sm font-medium
                text-[#1D1D1F] hover:bg-[#F5F5F7] transition-colors font-sidebar"
            >
              {label}
              {activeSection === id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </button>
            {activeSection === id && (
              <div className="px-4 pb-4">
                {id === 'model' && <ModelSettings />}
                {id === 'tools' && <ToolToggles />}
                {id === 'filemode' && <FileModeSettings />}
                {id === 'rag' && <RagSettings />}
                {id === 'reflection' && <ReflectionSettings />}
                {id === 'prompt' && <SystemPrompt />}
              </div>
            )}
          </div>
        ))}
      </div>

      {saved && (
        <div className="px-4 py-2 text-xs text-[#30B158] font-sidebar bg-green-50 border-t border-green-200">
          ✅ 设置已保存（下次创建 Agent 时生效）
        </div>
      )}
    </aside>
  );
};
