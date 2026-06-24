import type { ReactNode } from 'react';
import type { SidebarSection } from './nav-config';
import './Sidebar.css';

export interface SidebarProps {
  sections: SidebarSection[];
  activeSectionId: string;
  activeItemId?: string;
  onSelectSection: (sectionId: string) => void;
  onSelectItem: (sectionId: string, itemId: string) => void;
  /** Collapse to the icon rail only (hide the context column). */
  collapsed?: boolean;
  /** Brand mark shown at the top of the rail. */
  brand?: ReactNode;
}

/**
 * Two-column navigation: a 48px icon rail of sections plus a context column
 * listing the active section's items. Presentational and data-driven (see
 * SidebarSection) — the app supplies localized labels, icons, and selection
 * handlers. Mirrors the `.lazyweb` two-column sidebar variant.
 */
export function Sidebar({
  sections,
  activeSectionId,
  activeItemId,
  onSelectSection,
  onSelectItem,
  collapsed = false,
  brand = 'AC',
}: SidebarProps) {
  const activeSection = sections.find((section) => section.id === activeSectionId);

  return (
    <nav className="ac-sidebar" aria-label="Primary">
      <div className="ac-sidebar__rail">
        <span className="ac-sidebar__brand" aria-hidden="true">
          {brand}
        </span>
        {sections.map((section) => {
          const isActive = section.id === activeSectionId;
          return (
            <button
              key={section.id}
              type="button"
              className={
                isActive
                  ? 'ac-sidebar__icon ac-sidebar__icon--active'
                  : 'ac-sidebar__icon'
              }
              aria-label={section.label}
              aria-current={isActive ? 'page' : undefined}
              title={section.label}
              onClick={() => onSelectSection(section.id)}
            >
              {section.icon}
            </button>
          );
        })}
      </div>

      {!collapsed && activeSection != null && (
        <div className="ac-sidebar__list">
          <div className="ac-sidebar__group">{activeSection.label}</div>
          {activeSection.items.map((item) => {
            const isActive = item.id === activeItemId;
            return (
              <button
                key={item.id}
                type="button"
                className={
                  isActive
                    ? 'ac-sidebar__item ac-sidebar__item--active'
                    : 'ac-sidebar__item'
                }
                aria-current={isActive ? 'page' : undefined}
                onClick={() => onSelectItem(activeSection.id, item.id)}
              >
                <span className="ac-sidebar__item-label">{item.label}</span>
                {item.badge != null && (
                  <span className="ac-sidebar__badge">{item.badge}</span>
                )}
                {item.shortcut != null && (
                  <span className="ac-sidebar__shortcut">{item.shortcut}</span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </nav>
  );
}
