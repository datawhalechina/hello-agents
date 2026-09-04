import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  className?: string;
  type?: 'button' | 'submit';
}

const variants = {
  primary: 'bg-[#0066CC] text-white hover:bg-[#0077ED]',
  secondary: 'bg-[#ECEDF0] text-[#1D1D1F] hover:bg-[#E5E5EA]',
  ghost: 'bg-transparent text-[#0066CC] hover:bg-[#F0F0F2]',
  danger: 'bg-[#FF3B30] text-white hover:bg-red-600',
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs rounded-md',
  md: 'px-4 py-2 text-sm rounded-lg',
  lg: 'px-6 py-3 text-base rounded-xl',
};

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  className = '',
  type = 'button',
}) => (
  <button
    type={type}
    onClick={onClick}
    disabled={disabled}
    className={`inline-flex items-center justify-center gap-2 font-medium transition-all duration-200
      ${variants[variant]} ${sizes[size]}
      ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer active:scale-[0.97]'}
      ${className}`}
  >
    {children}
  </button>
);
