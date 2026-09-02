import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Pencil, X, CheckCircle2, ChevronDown } from 'lucide-react';
import { useModels } from '../../hooks/useModels';
import { Button } from '../shared/Button';
import { Toast } from '../shared/Toast';
import type { ModelEntry } from '../../types/config';

interface ToastState {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
}

interface FormState {
  name: string;
  label: string;
  base_url: string;
  api_key: string;
  model: string;
}

const emptyForm: FormState = { name: '', label: '', base_url: '', api_key: '', model: '' };

const Field: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  disabled?: boolean;
}> = ({ label, value, onChange, placeholder, type = 'text', disabled = false }) => (
  <div>
    <label className="block text-[11px] font-medium text-[#6E6E73] mb-1 font-sidebar">{label}</label>
    <input
      type={type}
      value={value}
      disabled={disabled}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-1.5 text-sm rounded-lg border border-[#E5E5EA] bg-white
        focus:outline-none focus:border-[#0066CC] focus:ring-1 focus:ring-[#0066CC]/20 font-body
        disabled:bg-[#F0F0F2] disabled:text-[#AEAEB2]"
    />
  </div>
);

interface AuxBlockProps {
  title: string;
  config: { label: string; base_url: string; api_key: string; model: string } | null;
  onSave: (patch: { label: string; base_url: string; model: string; api_key?: string }) => Promise<{ warning?: string }>;
  notify: (message: string, type?: ToastState['type']) => void;
  showReindexWarning?: boolean;
}

/** Embedding / Reranker 单例配置卡片：展示当前配置 + 编辑表单 */
const AuxBlock: React.FC<AuxBlockProps> = ({ title, config, onSave, notify, showReindexWarning }) => {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ label: '', base_url: '', api_key: '', model: '' });
  const [busy, setBusy] = useState(false);

  const openEdit = () => {
    if (!config) return;
    // api_key 不回填（后端只返回掩码，回填会覆盖真实 key）；留空 = 保留原 key
    setForm({ label: config.label, base_url: config.base_url, api_key: '', model: config.model });
    setEditing(true);
  };

  const handleSave = async () => {
    if (!form.model.trim()) {
      notify('请填写模型名 (model)', 'error');
      return;
    }
    setBusy(true);
    try {
      const res = await onSave({
        label: form.label,
        base_url: form.base_url.trim(),
        model: form.model.trim(),
        ...(form.api_key.trim() ? { api_key: form.api_key.trim() } : {}),
      });
      setEditing(false);
      notify(res.warning || '已保存', res.warning ? 'warning' : 'success');
    } catch (err: unknown) {
      notify(err instanceof Error ? err.message : '操作失败', 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border border-[#E5E5EA] bg-white p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-[#1D1D1F] font-sidebar">{title}</span>
        {!editing && (
          <Button variant="secondary" size="sm" onClick={openEdit} disabled={!config}>
            <Pencil size={12} /> 编辑
          </Button>
        )}
      </div>

      {showReindexWarning && (
        <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-800 font-body">
          切换 Embedding 模型后，已入库向量与新模型不兼容，请删除并重新上传知识库文件（反思笔记同理）。
        </div>
      )}

      {editing ? (
        <div className="mt-2 space-y-2">
          <Field
            label="显示名 (label)"
            value={form.label}
            onChange={(v) => setForm((f) => ({ ...f, label: v }))}
          />
          <Field
            label="API 地址 (base_url)"
            value={form.base_url}
            onChange={(v) => setForm((f) => ({ ...f, base_url: v }))}
            placeholder="留空 = DashScope 内置；非空 = OpenAI 兼容端点"
          />
          <Field
            label="API Key"
            type="password"
            value={form.api_key}
            onChange={(v) => setForm((f) => ({ ...f, api_key: v }))}
            placeholder="留空则保留原 key / 使用环境变量"
          />
          <Field
            label="模型名 (model)"
            value={form.model}
            onChange={(v) => setForm((f) => ({ ...f, model: v }))}
            placeholder="如 text-embedding-v4 / gte-rerank-v2"
          />
          <div className="flex gap-2">
            <Button variant="primary" size="sm" onClick={handleSave} disabled={busy}>
              {busy ? '保存中...' : '保存'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
              取消
            </Button>
          </div>
        </div>
      ) : config ? (
        <div className="mt-1.5 space-y-0.5 text-[11px] text-[#6E6E73] font-body break-all">
          <div>
            <span className="text-[#AEAEB2] font-sidebar">model:</span> {config.model}
          </div>
          <div>
            <span className="text-[#AEAEB2] font-sidebar">base_url:</span>{' '}
            {config.base_url || 'DashScope（环境变量）'}
          </div>
          <div>
            <span className="text-[#AEAEB2] font-sidebar">api_key:</span>{' '}
            {config.api_key ? `已设置 (${config.api_key})` : '未设置（使用环境变量）'}
          </div>
        </div>
      ) : (
        <p className="mt-1.5 text-[11px] text-[#AEAEB2] font-sidebar">加载中...</p>
      )}
    </div>
  );
};

export const ModelSettings: React.FC = () => {
  const {
    models,
    active,
    loading,
    refresh,
    addModel,
    updateModel,
    deleteModel,
    setActiveModel,
    embedding,
    reranker,
    updateEmbedding,
    updateReranker,
  } = useModels();
  const [showForm, setShowForm] = useState(false);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [auxOpen, setAuxOpen] = useState(false);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const showToast = (message: string, type: ToastState['type'] = 'success') => {
    setToast({ message, type });
  };

  const openAdd = () => {
    setEditingName(null);
    setForm(emptyForm);
    setShowForm(true);
  };

  const openEdit = (m: ModelEntry) => {
    setEditingName(m.name);
    // api_key 不回填（后端只返回掩码，回填会覆盖真实 key）；留空 = 保留原 key
    setForm({ name: m.name, label: m.label, base_url: m.base_url, api_key: '', model: m.model });
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!form.model.trim()) {
      showToast('请填写模型名 (model)', 'error');
      return;
    }
    if (!editingName && !form.name.trim()) {
      showToast('请填写模型标识 (name)', 'error');
      return;
    }
    setSaving(true);
    try {
      if (editingName) {
        await updateModel(editingName, {
          label: form.label,
          base_url: form.base_url,
          model: form.model.trim(),
          ...(form.api_key.trim() ? { api_key: form.api_key.trim() } : {}),
        });
        showToast('模型已更新');
      } else {
        await addModel({
          name: form.name.trim(),
          label: form.label,
          base_url: form.base_url.trim(),
          api_key: form.api_key.trim(),
          model: form.model.trim(),
        });
        showToast('模型已添加');
      }
      setShowForm(false);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '操作失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSetActive = async (name: string) => {
    if (name === active) return;
    try {
      await setActiveModel(name);
      showToast('已切换，新会话立即使用该模型；已打开的对话请刷新后使用', 'success');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '切换失败', 'error');
    }
  };

  const handleDelete = async (m: ModelEntry) => {
    if (!window.confirm(`确定删除模型「${m.label || m.name}」？`)) return;
    try {
      await deleteModel(m.name);
      showToast('模型已删除');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '删除失败', 'error');
    }
  };

  return (
    <div className="space-y-4">
      {/* 模型列表 */}
      {loading && models.length === 0 ? (
        <p className="text-[11px] text-[#AEAEB2] font-sidebar">加载中...</p>
      ) : models.length === 0 ? (
        <p className="text-[11px] text-[#AEAEB2] font-sidebar">尚未配置模型。点击下方"添加模型"开始。</p>
      ) : (
        <div className="space-y-2">
          {models.map((m) => {
            const isActive = m.name === active;
            return (
              <div
                key={m.name}
                className={`rounded-lg border p-3 transition-colors ${
                  isActive ? 'border-[#0066CC]/40 bg-blue-50/40' : 'border-[#E5E5EA] bg-white'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-sm font-medium text-[#1D1D1F] font-sidebar truncate">
                      {m.label || m.name}
                    </span>
                    {isActive && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-[#30B158] font-sidebar shrink-0">
                        <CheckCircle2 size={12} /> 当前
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {!isActive && (
                      <Button variant="secondary" size="sm" onClick={() => handleSetActive(m.name)}>
                        设为当前
                      </Button>
                    )}
                    <button
                      onClick={() => openEdit(m)}
                      title="编辑"
                      className="p-1.5 rounded-md text-[#6E6E73] hover:text-[#1D1D1F] hover:bg-[#F0F0F2] transition-colors"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(m)}
                      title="删除"
                      className="p-1.5 rounded-md text-[#6E6E73] hover:text-[#FF3B30] hover:bg-red-50 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                <div className="mt-1.5 space-y-0.5 text-[11px] text-[#6E6E73] font-body break-all">
                  <div>
                    <span className="text-[#AEAEB2] font-sidebar">model:</span> {m.model}
                  </div>
                  <div>
                    <span className="text-[#AEAEB2] font-sidebar">base_url:</span>{' '}
                    {m.base_url || 'DeepSeek（环境变量）'}
                  </div>
                  <div>
                    <span className="text-[#AEAEB2] font-sidebar">api_key:</span>{' '}
                    {m.api_key ? `已设置 (${m.api_key})` : '未设置（使用环境变量）'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 添加 / 编辑表单 */}
      {showForm && (
        <div className="rounded-lg border border-[#E5E5EA] bg-[#F9F9FB] p-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#1D1D1F] font-sidebar">
              {editingName ? '编辑模型' : '添加模型'}
            </span>
            <button
              onClick={() => setShowForm(false)}
              className="text-[#6E6E73] hover:text-[#1D1D1F] transition-colors"
            >
              <X size={14} />
            </button>
          </div>
          {!editingName && (
            <Field
              label="标识 (name，唯一，创建后不可改)"
              value={form.name}
              onChange={(v) => setForm((f) => ({ ...f, name: v }))}
              placeholder="如 my-provider"
            />
          )}
          <Field
            label="显示名 (label)"
            value={form.label}
            onChange={(v) => setForm((f) => ({ ...f, label: v }))}
            placeholder="如 My Model"
          />
          <Field
            label="API 地址 (base_url)"
            value={form.base_url}
            onChange={(v) => setForm((f) => ({ ...f, base_url: v }))}
            placeholder="https://api.example.com/v1（留空 = 内置 DeepSeek）"
          />
          <Field
            label="API Key"
            type="password"
            value={form.api_key}
            onChange={(v) => setForm((f) => ({ ...f, api_key: v }))}
            placeholder={editingName ? '留空则保留原 key' : '留空则使用环境变量'}
          />
          <Field
            label="模型名 (model)"
            value={form.model}
            onChange={(v) => setForm((f) => ({ ...f, model: v }))}
            placeholder="如 gpt-4o-mini / deepseek-chat"
          />
          <div className="flex gap-2">
            <Button variant="primary" size="sm" onClick={handleSubmit} disabled={saving}>
              {saving ? '保存中...' : '保存'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
              取消
            </Button>
          </div>
        </div>
      )}

      {/* 添加按钮 + 更多模型配置展开入口 */}
      {!showForm && (
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={openAdd} className="flex-1">
            <Plus size={14} /> 添加模型
          </Button>
          <button
            type="button"
            onClick={() => setAuxOpen((o) => !o)}
            title={auxOpen ? '收起更多模型配置' : '展开更多模型配置'}
            className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md
              border border-[#D2D2D7] bg-transparent text-[#6E6E73]
              hover:bg-[#F0F0F2] hover:text-[#1D1D1F] transition-all cursor-pointer shrink-0"
          >
            <ChevronDown size={12} className={`transition-transform ${auxOpen ? 'rotate-180' : ''}`} />
            {auxOpen ? '收起更多模型配置' : '展开更多模型配置'}
          </button>
        </div>
      )}

      {/* Embedding / Reranker 辅助模型配置（默认折叠，展开后 Reranker 在前、Embedding 在后） */}
      {auxOpen && (
        <div className="pt-1 space-y-3">
          <AuxBlock title="Reranker 模型" config={reranker} onSave={updateReranker} notify={showToast} />
          <AuxBlock
            title="Embedding 模型"
            config={embedding}
            onSave={updateEmbedding}
            notify={showToast}
            showReindexWarning
          />
        </div>
      )}

      <p className="text-[11px] text-[#AEAEB2] font-sidebar">
        当前 active 模型驱动主对话、会话标题、RAG 总结与文件切分。Embedding 用于知识库向量化，Reranker 用于检索重排；base_url 留空走 DashScope 内置，非空走 OpenAI 兼容端点。
      </p>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
};
