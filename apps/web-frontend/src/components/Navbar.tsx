/**
 * Navbar Component (Web Version)
 * Top navigation bar with app branding and auth status
 */

import { useTranslation } from 'react-i18next';
import { User, LogOut, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from './ui/dropdown-menu';
import { cn } from '../lib/utils';
import { useAuthStore } from '../store/auth-store';

interface NavbarProps {
  /** Callback when user clicks settings */
  onSettingsClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

export function Navbar({
  onSettingsClick,
  className
}: NavbarProps) {
  const { t } = useTranslation(['common', 'navigation']);
  const { isAuthenticated, user, isVerifying, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
  };

  return (
    <nav
      className={cn(
        'flex h-14 items-center justify-between border-b bg-background px-6',
        className
      )}
    >
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-600">
          <span className="text-sm font-bold text-white">AC</span>
        </div>
        <div className="flex flex-col">
          <h1 className="text-sm font-semibold leading-none">
            {t('common:appName')}
          </h1>
          <span className="text-xs text-muted-foreground">
            {t('navigation:messages.welcomeBack')}
          </span>
        </div>
      </div>

      {/* Right side: Auth status & user menu */}
      <div className="flex items-center gap-4">
        {isVerifying ? (
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              {t('common:labels.loading')}
            </span>
          </div>
        ) : isAuthenticated && user ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="flex items-center gap-2"
              >
                <User className="h-4 w-4" />
                <span className="hidden sm:inline-block">
                  {user.name || user.email || t('common:labels.user', { defaultValue: 'User' })}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="flex flex-col space-y-1 p-2">
                {user.name && (
                  <p className="text-sm font-medium">{user.name}</p>
                )}
                {user.email && (
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                )}
              </div>
              <DropdownMenuSeparator />
              {onSettingsClick && (
                <DropdownMenuItem onClick={onSettingsClick}>
                  {t('navigation:actions.settings')}
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                {t('navigation:actions.logout')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {t('common:labels.notAuthenticated', { defaultValue: 'Not authenticated' })}
            </span>
          </div>
        )}
      </div>
    </nav>
  );
}
