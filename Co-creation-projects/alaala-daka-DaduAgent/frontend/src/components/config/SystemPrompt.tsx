import React, { useState, useEffect } from 'react';
import { useConfig } from '../../hooks/useConfig';
import { Button } from '../shared/Button';

export const SystemPrompt: React.FC = () => {
  const { currentConfig, loadConfig, updateConfig } = useConfig();
  const [prompt, setPrompt] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadConfig('agent'); }, [loadConfig]);

  const handleSave = async () => {
    setSaving(true);
    // 系统提示词通过 prompt 文件管理，此处演示配置保存
    await updateConfig('agent', { _system_prompt_draft: prompt });
    setSaving(false);
  };

  return (
    <div className="space-y-3">
      <p className="text-xs text-[#AEAEB2] font-sidebar">
        编辑 Agent 系统提示词（通过修改 prompt/system_prompt.txt 生效）
      </p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={6}
        placeholder="系统提示词内容..."
        className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-[#E5E5EA] resize-y
          focus:outline-none focus:border-[#0066CC] focus:ring-1 focus:ring-[#0066CC]/20"
      />
      <div className="flex gap-2">
        <Button variant="primary" size="sm" onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存提示词'}
        </Button>
      </div>
    </div>
  );
};
