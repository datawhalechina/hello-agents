import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

const variantClasses = {
  default: 'bg-[#ECEDF0] text-[#6E6E73]',
  success: 'bg-green-100 text-green-700',
  warning: 'bg-amber-100 text-amber-700',
  danger: 'bg-red-100 text-red-700',
};

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default' }) => (
  <span className={`inline-flex items-center px-2 py-0.5 text-[11px] font-medium rounded-full ${variantClasses[variant]}`}>
    {children}
  </span>
);
