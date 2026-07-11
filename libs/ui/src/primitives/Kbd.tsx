import type { ReactNode } from 'react';
import './Kbd.css';

export interface KbdProps {
  children: ReactNode;
}

/** Inline keyboard-hint text (e.g. a "⌘K" shortcut label). */
export function Kbd({ children }: Readonly<KbdProps>) {
  return <span className="ac-kbd">{children}</span>;
}
