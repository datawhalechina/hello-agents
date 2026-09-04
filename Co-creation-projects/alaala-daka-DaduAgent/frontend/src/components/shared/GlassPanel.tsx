import React from 'react';

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
}

export const GlassPanel: React.FC<GlassPanelProps> = ({ children, className = '' }) => (
  <div
    className={`glass border border-[#E5E5EA] rounded-xl shadow-sm ${className}`}
  >
    {children}
  </div>
);
