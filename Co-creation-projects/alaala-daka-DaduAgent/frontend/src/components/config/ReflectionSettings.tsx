import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Plus, Pencil, Trash2, X, ChevronDown, ChevronRight } from 'lucide-react';
import { useReflections } from '../../hooks/useReflections';
import { Button } from '../shared/Button';
import { Badge } from '../shared/Badge';
import { Toast } from '../shared/Toast';
import { Spinner } from '../shared/Spinner';
import type { ReflectionEntry } from '../../types/config';

const SEVERITY_LABEL: Record<string, string> = { fatal: '致命', high: '严重', medium: '一般', low: '轻微' };
const SEVERITY_COLOR: Record<string, string> = { fatal: '#FF3B30', high: '#FF9F0A', medium: '#FFD60A', low: '#30B158' };
const SEVERITY_OPTIONS = ['fatal', 'high', 'medium', 'low'];
const PAGE_SIZE = 5;

interface ToastState {
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
}

interface FormState {
  error_desc: string;
  solution: string;
  philosophy: string;
  tags: string;
  severity: string;
}

const emptyForm: FormState = { error_desc: '', solution: '', philosophy: '', tags: '', severity: 'medium' };

/** 把一条笔记组合成 markdown 文本，列表预览与编辑实时预览共用 */
function toMarkdown(r: {
  ref_id: string;
  error_desc: string;
  solution: string;
  philosophy: string;
  tags: string;
  severity: string;
  timestamp: string;
  updated_at?: string;
}): string {
  const tags = (r.tags || 'general').split(',').map((t) => t.trim()).filter(Boolean);
  const tagLine = tags.length ? `**标签：**${tags.map((t) => `\`${t}\``).join(' ')}` : '';
  const sev = SEVERITY_LABEL[r.severity] ?? r.severity;
  return [
    `> **严重程度：${sev}**　**ref_id：** \`${r.ref_id}\``,
    tagLine,
    '',
    '## 错误描述',
    r.error_desc,
    '',
    '## 解决方案',
    r.solution,
    '',
    '## 哲学理解',
    r.philosophy,
    '',
    '---',
    `📅 ${r.timestamp}${r.updated_at ? ` · 更新于 ${r.updated_at}` : ''}`,
  ].join('\n');
}

const TextAreaField: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
}> = ({ label, value, onChange, placeholder, rows = 4 }) => (
  <div>
    <label className="block text-[11px] font-medium text-[#6E6E73] mb-1 font-sidebar">{label}</label>
    <textarea
      value={value}
      rows={rows}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-1.5 text-sm rounded-lg border border-[#E5E5EA] bg-white
        focus:outline-none focus:border-[#0066CC] focus:ring-1 focus:ring-[#0066CC]/20 font-body
        resize-none whitespace-pre-wrap"
    />
  </div>
);

export const ReflectionSettings: React.FC = () => {
  const { reflections, loading, create, update, remove } = useReflections();
  const [editingRefId, setEditingRefId] = useState<string | null>(null); // null=列表 | 'new'=新增 | ref_id=编辑
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string | null>(null); // null = 全部
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const editingEntry =
    editingRefId && editingRefId !== 'new'
      ? reflections.find((r) => r.ref_id === editingRefId)
      : undefined;

  const showToast = (message: string, type: ToastState['type'] = 'success') => {
    setToast({ message, type });
  };

  const openAdd = () => {
    setForm(emptyForm);
    setEditingRefId('new');
    setVisibleCount(PAGE_SIZE);
  };

  const openEdit = (r: ReflectionEntry) => {
    setForm({
      error_desc: r.error_desc,
      solution: r.solution,
      philosophy: r.philosophy,
      tags: r.tags,
      severity: r.severity,
    });
    setEditingRefId(r.ref_id);
    setVisibleCount(PAGE_SIZE);
  };

  const closeForm = () => {
    setEditingRefId(null);
    setExpandedId(null);
    setVisibleCount(PAGE_SIZE);
  };

  const handleSubmit = async () => {
    if (!form.error_desc.trim() || !form.solution.trim() || !form.philosophy.trim()) {
      showToast('错误描述 / 解决方案 / 哲学理解 不能为空', 'error');
      return;
    }
    setSaving(true);
    try {
      if (editingRefId === 'new') {
        await create({
          error_desc: form.error_desc.trim(),
          solution: form.solution.trim(),
          philosophy: form.philosophy.trim(),
          tags: form.tags.trim() || 'general',
          severity: form.severity,
        });
        showToast('反思笔记已添加');
      } else if (editingRefId) {
        await update(editingRefId, {
          error_desc: form.error_desc.trim(),
          solution: form.solution.trim(),
          philosophy: form.philosophy.trim(),
          tags: form.tags.trim(),
          severity: form.severity,
        });
        showToast('反思笔记已更新');
      }
      closeForm();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '操作失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (r: ReflectionEntry) => {
    if (!window.confirm(`确定删除反思笔记 [${r.ref_id}]？`)) return;
    try {
      await remove(r.ref_id);
      showToast('反思笔记已删除');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : '删除失败', 'error');
    }
  };

  // ── 列表态 ──
  if (editingRefId === null) {
    // 后端已按严重程度降序 + 同级 timestamp 倒序返回；此处只做过滤 + 分页切片
    const filtered = severityFilter
      ? reflections.filter((r) => r.severity === severityFilter)
      : reflections;
    const visible = filtered.slice(0, visibleCount);
    const hasMore = visibleCount < filtered.length;
    const remaining = filtered.length - visibleCount;

    return (
      <div className="space-y-4">
        {/* 头部 */}
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-[#1D1D1F] font-sidebar">
            反思笔记 ({reflections.length})
          </span>
          <Button variant="secondary" size="sm" onClick={openAdd}>
            <Plus size={14} /> 新增笔记
          </Button>
        </div>

        {/* 严重程度筛选 */}
        <div className="flex flex-wrap gap-1.5">
          {[
            { value: null, label: '全部', count: reflections.length },
            ...SEVERITY_OPTIONS.map((s) => ({
              value: s,
              label: SEVERITY_LABEL[s],
              count: reflections.filter((r) => r.severity === s).length,
            })),
          ].map((opt) => {
            const active = severityFilter === opt.value;
            return (
              <button
                key={opt.value ?? 'all'}
                onClick={() => {
                  setSeverityFilter(opt.value);
                  setVisibleCount(PAGE_SIZE);
                }}
                className={`px-2 py-1 rounded-full text-[11px] border transition-colors font-sidebar ${
                  active
                    ? 'bg-[#0066CC]/10 text-[#0066CC] border-[#0066CC]/30'
                    : 'bg-white text-[#6E6E73] border-[#E5E5EA] hover:border-[#0066CC]/40 hover:text-[#1D1D1F]'
                }`}
              >
                {opt.label} ({opt.count})
              </button>
            );
          })}
        </div>

        {loading && reflections.length === 0 ? (
          <div className="flex items-center justify-center py-6">
            <Spinner />
          </div>
        ) : reflections.length === 0 ? (
          <p className="text-[11px] text-[#AEAEB2] font-sidebar">
            暂无反思笔记。Agent 完成任务后会沉淀经验教训，也可点击"新增笔记"手动记录。
          </p>
        ) : filtered.length === 0 ? (
          <p className="text-[11px] text-[#AEAEB2] font-sidebar">
            该严重程度下暂无反思笔记。
          </p>
        ) : (
          <div className="space-y-2">
            {visible.map((r) => {
              const isExpanded = expandedId === r.ref_id;
              const tags = (r.tags || 'general').split(',').map((t) => t.trim()).filter(Boolean);
              return (
                <div
                  key={r.ref_id}
                  className="rounded-lg border border-[#E5E5EA] bg-white p-3 transition-colors"
                >
                  {/* 首行：级别 + ref_id + 操作 */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span
                        className="inline-block w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: SEVERITY_COLOR[r.severity] ?? '#AEAEB2' }}
                      />
                      <span className="text-sm font-medium text-[#1D1D1F] font-sidebar truncate">
                        {SEVERITY_LABEL[r.severity] ?? r.severity}
                      </span>
                      <span className="text-[11px] text-[#6E6E73] font-mono shrink-0">[{r.ref_id}]</span>
                    </div>
                    <div className="flex items-center gap-0.5 shrink-0">
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : r.ref_id)}
                        title={isExpanded ? '收起' : '展开'}
                        className="p-1.5 rounded-md text-[#6E6E73] hover:text-[#1D1D1F] hover:bg-[#F0F0F2] transition-colors"
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </button>
                      <button
                        onClick={() => openEdit(r)}
                        title="编辑"
                        className="p-1.5 rounded-md text-[#6E6E73] hover:text-[#1D1D1F] hover:bg-[#F0F0F2] transition-colors"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(r)}
                        title="删除"
                        className="p-1.5 rounded-md text-[#6E6E73] hover:text-[#FF3B30] hover:bg-red-50 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  {/* 标签 chips */}
                  {tags.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {tags.map((t) => (
                        <Badge key={t} variant="default">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* 摘要 */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : r.ref_id)}
                    className="mt-1.5 block w-full text-left text-[12px] text-[#6E6E73] font-body leading-snug line-clamp-2 hover:text-[#1D1D1F] transition-colors"
                  >
                    {r.error_desc}
                  </button>

                  <div className="mt-1 text-[10px] text-[#AEAEB2] font-sidebar">
                    📅 {r.timestamp}
                    {r.updated_at ? ` · 更新于 ${r.updated_at}` : ''}
                  </div>

                  {/* 展开：markdown 预览 */}
                  {isExpanded && (
                    <div className="mt-2 pt-2 border-t border-[#E5E5EA]">
                      <div className="markdown-body text-[12px] leading-relaxed">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{toMarkdown(r)}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* "⌵" 展开更多：最后一条卡片右下侧，每次 +5 */}
            {hasMore && (
              <div className="flex justify-end">
                <button
                  onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
                  className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-[#6E6E73]
                    hover:text-[#1D1D1F] hover:bg-[#F0F0F2] transition-colors font-sidebar"
                >
                  <span className="text-sm leading-none">⌵</span>
                  展开后续 {Math.min(PAGE_SIZE, remaining)} 条（剩余 {remaining}）
                </button>
              </div>
            )}
          </div>
        )}

        <p className="text-[11px] text-[#AEAEB2] font-sidebar">
          ref_id / timestamp / updated_at 由系统维护，不可修改。新增笔记时 id 自动取当前最大编号 +1，删除后不复用、不重排。
        </p>

        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    );
  }

  // ── 新增 / 编辑表单态 ──
  const isNew = editingRefId === 'new';
  const preview = toMarkdown({
    ref_id: isNew ? 'ref_?' : editingRefId,
    ...form,
    timestamp: isNew ? '刚刚' : (editingEntry?.timestamp ?? ''),
    updated_at: isNew ? undefined : (editingEntry?.updated_at ?? ''),
  });

  return (
    <div className="space-y-3">
      {/* 标题 + 关闭 */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[#1D1D1F] font-sidebar">
          {isNew ? '新增反思笔记' : `编辑 ${editingRefId}`}
        </span>
        <button onClick={closeForm} className="text-[#6E6E73] hover:text-[#1D1D1F] transition-colors">
          <X size={14} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* 左列：结构化字段 */}
        <div className="space-y-3 min-w-0">
          <TextAreaField
            label="错误描述（教训）"
            value={form.error_desc}
            onChange={(v) => setForm((f) => ({ ...f, error_desc: v }))}
            placeholder="如：忘记处理空指针"
            rows={4}
          />
          <TextAreaField
            label="解决方案"
            value={form.solution}
            onChange={(v) => setForm((f) => ({ ...f, solution: v }))}
            placeholder="如：添加 is None 检查"
            rows={3}
          />
          <TextAreaField
            label="哲学理解"
            value={form.philosophy}
            onChange={(v) => setForm((f) => ({ ...f, philosophy: v }))}
            placeholder="如：永远先考虑边界条件"
            rows={3}
          />
          <div>
            <label className="block text-[11px] font-medium text-[#6E6E73] mb-1 font-sidebar">标签（逗号分隔）</label>
            <input
              type="text"
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
              placeholder="如 空指针,边界条件"
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-[#E5E5EA] bg-white
                focus:outline-none focus:border-[#0066CC] focus:ring-1 focus:ring-[#0066CC]/20 font-body"
            />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-[#6E6E73] mb-1 font-sidebar">严重程度</label>
            <select
              value={form.severity}
              onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value }))}
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-[#E5E5EA] bg-white
                focus:outline-none focus:border-[#0066CC] focus:ring-1 focus:ring-[#0066CC]/20 font-body"
            >
              {SEVERITY_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {SEVERITY_LABEL[s]} ({s})
                </option>
              ))}
            </select>
          </div>
          <p className="text-[10px] text-[#AEAEB2] font-sidebar">
            ref_id / timestamp / updated_at 由系统维护，不可修改。
          </p>
        </div>

        {/* 右列：实时 markdown 预览 */}
        <div className="border border-[#E5E5EA] rounded-lg bg-white p-3 h-[400px] overflow-y-auto min-w-0">
          <div className="text-[11px] text-[#AEAEB2] font-sidebar mb-1">实时预览</div>
          <div className="markdown-body text-[12px] leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{preview}</ReactMarkdown>
          </div>
        </div>
      </div>

      {/* 保存 / 取消 */}
      <div className="flex gap-2">
        <Button variant="primary" size="sm" onClick={handleSubmit} disabled={saving}>
          {saving ? '保存中...' : '保存'}
        </Button>
        <Button variant="ghost" size="sm" onClick={closeForm}>
          取消
        </Button>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
};
