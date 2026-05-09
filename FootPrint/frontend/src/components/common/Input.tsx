'use client';

import { forwardRef, type InputHTMLAttributes } from 'react';
import { type UseFormRegisterReturn } from 'react-hook-form';
import { cn } from '@/lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  register?: UseFormRegisterReturn;
  required?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, register, required, className, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s/g, '-');

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-[13px] font-bold text-[#44403C]"
          >
            {label}
            {required && <span className="text-[#F97316] ml-0.5">*</span>}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={cn(
            'w-full border-[1.5px] border-[#E7E5E4] rounded-[10px] px-3.5 py-2.5 text-[14px] text-[#1C1917] bg-white transition-colors outline-none',
            'placeholder:text-[#A8A29E]',
            'focus:border-[#F97316]',
            error && 'border-[#DC2626] focus:border-[#DC2626]',
            className
          )}
          {...register}
          {...props}
        />
        {error && (
          <p className="text-[12px] text-[#DC2626] mt-0.5">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
