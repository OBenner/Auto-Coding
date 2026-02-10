/**
 * Layout Component (Web Version)
 * Main layout wrapper with sidebar navigation and navbar
 */

import { useState, type ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar, type SidebarView } from './Sidebar';
import { Navbar } from './Navbar';
import { cn } from '../lib/utils';

interface LayoutProps {
  /** Child components to render in main content area */
  children?: ReactNode;
  /** Current active view for sidebar highlighting */
  activeView?: SidebarView;
  /** Callback when sidebar view changes */
  onViewChange?: (view: SidebarView) => void;
  /** Whether user is authenticated */
  isAuthenticated?: boolean;
  /** Current user info */
  user?: {
    name?: string;
    email?: string;
  };
  /** Callback when user logs out */
  onLogout?: () => void;
  /** Callback when settings is clicked */
  onSettingsClick?: () => void;
  /** Callback when new task is clicked */
  onNewTaskClick?: () => void;
}

export function Layout({
  children,
  activeView = 'kanban',
  onViewChange,
  isAuthenticated = false,
  user,
  onLogout,
  onSettingsClick,
  onNewTaskClick
}: LayoutProps) {
  const [currentView, setCurrentView] = useState<SidebarView>(activeView);

  const handleViewChange = (view: SidebarView) => {
    setCurrentView(view);
    onViewChange?.(view);
  };

  const handleSettingsClick = () => {
    onSettingsClick?.();
  };

  const handleNewTaskClick = () => {
    onNewTaskClick?.();
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar Navigation */}
      <Sidebar
        activeView={currentView}
        onViewChange={handleViewChange}
        onSettingsClick={handleSettingsClick}
        onNewTaskClick={handleNewTaskClick}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <Navbar
          isAuthenticated={isAuthenticated}
          user={user}
          onLogout={onLogout}
          onSettingsClick={handleSettingsClick}
        />

        {/* Content */}
        <main className={cn('flex-1 overflow-auto p-6')}>
          {children || <Outlet />}
        </main>
      </div>
    </div>
  );
}
