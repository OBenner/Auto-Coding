/**
 * Layout Component (Web Version)
 * Main layout wrapper with sidebar navigation and navbar
 * Enhanced with responsive design for mobile devices
 */

import { useState, type ReactNode } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { Sidebar, type SidebarView } from './Sidebar';
import { Navbar } from './Navbar';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

interface LayoutProps {
  /** Child components to render in main content area */
  children?: ReactNode;
  /** Current active view for sidebar highlighting */
  activeView?: SidebarView;
  /** Callback when sidebar view changes */
  onViewChange?: (view: SidebarView) => void;
  /** Callback when new task is clicked */
  onNewTaskClick?: () => void;
}

export function Layout({
  children,
  activeView = 'kanban',
  onViewChange,
  onNewTaskClick
}: LayoutProps) {
  const [currentView, setCurrentView] = useState<SidebarView>(activeView);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const navigate = useNavigate();

  const handleViewChange = (view: SidebarView) => {
    setCurrentView(view);
    onViewChange?.(view);
  };

  const handleSettingsClick = () => {
    navigate('/settings');
    // Close mobile sidebar when navigating
    setIsMobileSidebarOpen(false);
  };

  const handleNewTaskClick = () => {
    navigate('/create');
    // Close mobile sidebar when navigating
    setIsMobileSidebarOpen(false);
  };

  const toggleMobileSidebar = () => {
    setIsMobileSidebarOpen(!isMobileSidebarOpen);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar Navigation */}
      <Sidebar
        activeView={currentView}
        onViewChange={handleViewChange}
        onSettingsClick={handleSettingsClick}
        onNewTaskClick={handleNewTaskClick}
        isMobileOpen={isMobileSidebarOpen}
        onMobileClose={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <Navbar
          onSettingsClick={handleSettingsClick}
          onMenuClick={toggleMobileSidebar}
        />

        {/* Content */}
        <main className={cn(
          'flex-1 overflow-auto',
          // Responsive padding
          'p-4 sm:p-6 lg:p-6'
        )}>
          {children || <Outlet />}
        </main>
      </div>
    </div>
  );
}
