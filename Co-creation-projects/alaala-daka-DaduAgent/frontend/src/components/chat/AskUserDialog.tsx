import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { Button } from '../shared/Button';

interface AskUserDialogProps {
  question: string;
  requestId: string;
  onAnswer: (requestId: string, answer: 'approved' | 'rejected', detail?: string) => void;
  onDismiss: () => void;
}

export const AskUserDialog: React.FC<AskUserDialogProps> = ({
  question,
  requestId,
  onAnswer,
  onDismiss,
}) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm">
    <div className="glass-light border border-[#E5E5EA] rounded-2xl shadow-2xl p-6 max-w-md w-full mx-4 animate-fade-in">
      <div className="flex items-start gap-3 mb-4">
        <div className="p-2 rounded-full bg-amber-100 flex-shrink-0">
          <ShieldAlert size={20} className="text-[#FF9F0A]" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[#1D1D1F] font-sidebar mb-1">
            Agent 请求确认
          </h3>
          <p className="text-sm text-[#6E6E73] leading-relaxed">{question}</p>
        </div>
      </div>
      <div className="flex gap-3 justify-end">
        <Button variant="ghost" size="sm" onClick={onDismiss}>
          忽略
        </Button>
        <Button variant="secondary" size="sm" onClick={() => onAnswer(requestId, 'rejected')}>
          拒绝
        </Button>
        <Button variant="primary" size="sm" onClick={() => onAnswer(requestId, 'approved', '用户已批准')}>
          批准
        </Button>
      </div>
    </div>
  </div>
);
