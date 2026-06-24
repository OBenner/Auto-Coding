import type { ReactNode } from 'react';

/** A single navigable entry inside a sidebar section's context column. */
export interface SidebarItem {
  id: string;
  /** Display label (already localized by the app). */
  label: string;
  /** Optional keyboard-shortcut hint, e.g. "K" or "⌘N". */
  shortcut?: string;
  /** Optional badge — a count or short status text. */
  badge?: string | number;
}

/** A top-level section shown as an icon in the rail; owns a list of items. */
export interface SidebarSection {
  id: string;
  /** Section label — used as the icon's accessible name and the group header. */
  label: string;
  /** Section icon node shown in the rail (the app supplies the icon). */
  icon: ReactNode;
  items: SidebarItem[];
}
