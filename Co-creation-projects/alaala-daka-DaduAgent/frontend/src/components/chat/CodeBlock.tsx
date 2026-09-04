import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface CodeBlockProps {
  language: string;
  code: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-2 rounded-lg overflow-hidden border border-[#E5E5EA]">
      {/* 头部 */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#F5F5F7] border-b border-[#E5E5EA]">
        <span className="text-[11px] font-medium text-[#6E6E73] font-mono uppercase">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-0.5 text-[11px] text-[#6E6E73] rounded
            hover:bg-[#E5E5EA] transition-colors font-sidebar"
        >
          {copied ? <Check size={12} className="text-[#30B158]" /> : <Copy size={12} />}
          {copied ? '已复制' : '复制'}
        </button>
      </div>
      {/* 代码 */}
      <pre className="p-4 bg-[#1E1E1E] text-[#D4D4D4] text-sm font-mono leading-relaxed overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
};
