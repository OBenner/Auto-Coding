import type { HTMLAttributes } from 'react';
import './Kbd.css';

export type KbdProps = HTMLAttributes<HTMLElement>;

/**
 * Inline keyboard-hint text (e.g. a "⌘K" shortcut label), rendered as the
 * semantic <kbd> element. Remaining attributes are forwarded.
 */
export function Kbd({ className, children, ...rest }: Readonly<KbdProps>) {
  return (
    <kbd className={className ? `ac-kbd ${className}` : 'ac-kbd'} {...rest}>
      {children}
    </kbd>
  );
}
