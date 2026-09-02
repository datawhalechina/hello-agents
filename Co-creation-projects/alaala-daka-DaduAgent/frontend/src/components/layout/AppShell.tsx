import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { ConfigPanel } from './ConfigPanel';

interface AppShellProps {
  children: React.ReactNode;
  currentSessionId: string;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  configPanelOpen: boolean;
  onToggleConfig: () => void;
  onConfigPanelClose: () => void;
  refreshKey?: number;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  configPanelOpen,
  onToggleConfig,
  onConfigPanelClose,
  refreshKey,
}) => {
  return (
    <div className="h-screen flex overflow-hidden">
      {/* 侧边栏 — 磨砂玻璃 */}
      <Sidebar
        currentSessionId={currentSessionId}
        onSelectSession={onSelectSession}
        onNewSession={onNewSession}
        onToggleConfig={onToggleConfig}
        onDeleteSession={onDeleteSession}
        refreshKey={refreshKey}
      />

      {/* 主聊天区 */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#F5F5F7]">
        {children}
      </main>

      {/* 配置面板 — 右滑面板 */}
      {configPanelOpen && (
        <ConfigPanel onClose={onConfigPanelClose} />
      )}
    </div>
  );
};
