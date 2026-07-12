import type { InputHTMLAttributes } from 'react';
import './Input.css';

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

/**
 * Single-line text input in the `.lazyweb` field style (soft surface,
 * hairline border, visible focus ring). All input attributes forward.
 */
export function Input({ className, ...rest }: Readonly<InputProps>) {
  return (
    <input
      className={className ? `ac-input ${className}` : 'ac-input'}
      {...rest}
    />
  );
}
