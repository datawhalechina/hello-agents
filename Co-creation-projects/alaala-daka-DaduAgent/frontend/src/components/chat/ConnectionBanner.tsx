import React from 'react';
import { WifiOff } from 'lucide-react';

export const ConnectionBanner: React.FC = () => (
  <div className="flex items-center justify-center gap-2 px-4 py-2 bg-[#FFF3CD] border-b border-[#FFE69C]">
    <WifiOff size={14} className="text-[#FF9F0A]" />
    <span className="text-sm text-[#856404] font-sidebar">⚠️ 网络中断中：(</span>
  </div>
);
