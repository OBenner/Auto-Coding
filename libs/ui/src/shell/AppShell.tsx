import type { ReactNode } from 'react';
import './AppShell.css';

export interface AppShellProps {
  /** Left column — typically the Sidebar (icon rail + context column). */
  sidebar?: ReactNode;
  /** Top bar of the content column. */
  topbar?: ReactNode;
  /** Main scrollable region. Falls back to `children`. */
  main?: ReactNode;
  /** Bottom status bar of the content column. */
  statusbar?: ReactNode;
  children?: ReactNode;
}

/**
 * Layout primitive: a sidebar column plus a content column laid out as
 * topbar / main / statusbar. Pure layout — no business logic, no data.
 * Each slot renders only when provided.
 */
export function AppShell({
  sidebar,
  topbar,
  main,
  statusbar,
  children,
}: AppShellProps) {
  return (
    <div className="ac-shell">
      {sidebar != null && <div className="ac-shell__sidebar">{sidebar}</div>}
      <div className="ac-shell__content">
        {topbar != null && <header className="ac-shell__topbar">{topbar}</header>}
        <main className="ac-shell__main">{main ?? children}</main>
        {statusbar != null && (
          <footer className="ac-shell__statusbar">{statusbar}</footer>
        )}
      </div>
    </div>
  );
}
