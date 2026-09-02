import React, { useState, useEffect } from 'react';
import { useConfig } from '../../hooks/useConfig';
import { Button } from '../shared/Button';

export const FileModeSettings: React.FC = () => {
  const { currentConfig, loadConfig, updateConfig } = useConfig();
  const [mode, setMode] = useState('auto');
  const [maxRead, setMaxRead] = useState(1048576);
  const [maxWrite, setMaxWrite] = useState(5242880);
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadConfig('filemanage'); }, [loadConfig]);

  useEffect(() => {
    if (currentConfig.filemanage) {
      const cfg = currentConfig.filemanage;
      if (cfg.mode) setMode(cfg.mode as string);
      if (cfg.max_file_size_read) setMaxRead(cfg.max_file_size_read as number);
      if (cfg.max_file_size_write) setMaxWrite(cfg.max_file_size_write as number);
    }
  }, [currentConfig.filemanage]);

  const handleSave = async () => {
    setSaving(true);
    await updateConfig('filemanage', {
      mode,
      max_file_size_read: maxRead,
      max_file_size_write: maxWrite,
    });
    setSaving(false);
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-[#6E6E73] mb-1.5 font-sidebar">操作模式</label>
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          className="w-full px-3 py-2 text-sm rounded-lg border border-[#E5E5EA] bg-white
            focus:outline-none focus:border-[#0066CC] font-body"
        >
          <option value="auto">Auto — 自由 CRUD（安全边界内）</option>
          <option value="manual">Manual — 写操作需用户批准</option>
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium text-[#6E6E73] mb-1.5 font-sidebar">
          最大读取大小 (MB): {Math.round(maxRead / 1024 / 1024 * 10) / 10}
        </label>
        <input
          type="range"
          min={102400}
          max={10485760}
          step={102400}
          value={maxRead}
          onChange={(e) => setMaxRead(Number(e.target.value))}
          className="w-full accent-[#0066CC]"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-[#6E6E73] mb-1.5 font-sidebar">
          最大写入大小 (MB): {Math.round(maxWrite / 1024 / 1024 * 10) / 10}
        </label>
        <input
          type="range"
          min={102400}
          max={20971520}
          step={102400}
          value={maxWrite}
          onChange={(e) => setMaxWrite(Number(e.target.value))}
          className="w-full accent-[#0066CC]"
        />
      </div>

      <Button variant="primary" size="sm" onClick={handleSave} disabled={saving}>
        {saving ? '保存中...' : '保存文件管理设置'}
      </Button>
    </div>
  );
};
