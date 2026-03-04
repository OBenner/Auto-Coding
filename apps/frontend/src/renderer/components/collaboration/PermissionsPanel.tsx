/**
 * PermissionsPanel - Team Access Management for Specs
 *
 * Manages team member permissions for specs with role-based access control.
 * Supports read/write/admin permission levels and user management.
 *
 * Features:
 * - Display all users with access to a spec
 * - Add new users with specific permission levels
 * - Update existing user permissions
 * - Remove users from spec
 * - Visual indicators for permission levels
 *
 * @example
 * ```tsx
 * <PermissionsPanel
 *   specId="001-feature"
 *   onPermissionGranted={(permission) => console.log('Granted:', permission)}
 *   onPermissionUpdated={(permission) => console.log('Updated:', permission)}
 *   onPermissionRemoved={(userId) => console.log('Removed:', userId)}
 * />
 * ```
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  UserPlus,
  UserMinus,
  Edit3,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { cn } from '../../lib/utils';
import type { SpecPermission, PermissionLevel, CollaborationUser } from '../../../shared/types';

/**
 * Props for PermissionsPanel
 */
interface PermissionsPanelProps {
  /** Spec ID to manage permissions for */
  specId: string;
  /** Callback when a permission is granted */
  onPermissionGranted?: (permission: SpecPermission) => void;
  /** Callback when a permission is updated */
  onPermissionUpdated?: (permission: SpecPermission) => void;
  /** Callback when a permission is revoked */
  onPermissionRevoked?: (userId: string) => void;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Permission level with display info
 */
interface PermissionLevelInfo {
  level: PermissionLevel;
  label: string;
  description: string;
  icon: React.ReactNode;
  colorClass: string;
}

/**
 * Get permission level display information
 */
function getPermissionLevelInfo(level: PermissionLevel, t: (key: string) => string): PermissionLevelInfo {
  const levels: Record<PermissionLevel, PermissionLevelInfo> = {
    read: {
      level: 'read',
      label: t('collaboration:permissions.readLabel'),
      description: t('collaboration:permissions.read'),
      icon: <Shield className="h-4 w-4" />,
      colorClass: 'bg-blue-500/10 text-blue-500 border-blue-500/20'
    },
    write: {
      level: 'write',
      label: t('collaboration:permissions.writeLabel'),
      description: t('collaboration:permissions.write'),
      icon: <ShieldCheck className="h-4 w-4" />,
      colorClass: 'bg-green-500/10 text-green-500 border-green-500/20'
    },
    admin: {
      level: 'admin',
      label: t('collaboration:permissions.adminLabel'),
      description: t('collaboration:permissions.admin'),
      icon: <ShieldAlert className="h-4 w-4" />,
      colorClass: 'bg-purple-500/10 text-purple-500 border-purple-500/20'
    }
  };

  return levels[level];
}

/**
 * Permission Card Component
 */
interface PermissionCardProps {
  permission: SpecPermission;
  canEdit: boolean;
  onUpdate: (userId: string, level: PermissionLevel) => void;
  onRemove: (userId: string) => void;
}

function PermissionCard({ permission, canEdit, onUpdate, onRemove }: PermissionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState<PermissionLevel>(permission.level);
  const { t } = useTranslation(['collaboration', 'common']);

  const levelInfo = getPermissionLevelInfo(permission.level, t);
  const isNewUser = !permission.granted_at || permission.granted_at === '';

  const handleSaveUpdate = () => {
    if (selectedLevel !== permission.level) {
      onUpdate(permission.user.user_id, selectedLevel);
    }
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setSelectedLevel(permission.level);
    setIsEditing(false);
  };

  return (
    <Card className={cn('transition-all', isNewUser && 'border-info/50 bg-info/5')}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          {/* User Info */}
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
                {permission.user.username.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {permission.user.username}
                </p>
                {permission.user.email && (
                  <p className="text-xs text-muted-foreground">
                    {permission.user.email}
                  </p>
                )}
              </div>
            </div>

            {/* Permission Level */}
            {isEditing ? (
              <div className="flex items-center gap-2">
                <select
                  value={selectedLevel}
                  onChange={(e) => setSelectedLevel(e.target.value as PermissionLevel)}
                  className="text-sm rounded-md border border-input bg-background px-2 py-1"
                >
                  <option value="read">{t('collaboration:permissions.read')}</option>
                  <option value="write">{t('collaboration:permissions.write')}</option>
                  <option value="admin">{t('collaboration:permissions.admin')}</option>
                </select>
              </div>
            ) : (
              <Badge
                variant="outline"
                className={cn('flex items-center gap-1 text-xs w-fit', levelInfo.colorClass)}
              >
                {levelInfo.icon}
                {levelInfo.label}
              </Badge>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1">
            {canEdit ? (
              <>
                {isEditing ? (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleSaveUpdate}
                      className="h-8 w-8 p-0 text-success hover:bg-success/10"
                      title="Save changes"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCancelEdit}
                      className="h-8 w-8 p-0 text-muted-foreground hover:bg-muted"
                      title="Cancel"
                    >
                      <XCircle className="h-4 w-4" />
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsEditing(true)}
                      className="h-8 w-8 p-0 text-info hover:bg-info/10 hover:text-info"
                      title="Change permission level"
                    >
                      <Edit3 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onRemove(permission.user.user_id)}
                      className="h-8 w-8 p-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                      title="Remove access"
                    >
                      <UserMinus className="h-4 w-4" />
                    </Button>
                  </>
                )}
              </>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Add User Form Component
 */
interface AddUserFormProps {
  onAddUser: (username: string, level: PermissionLevel) => void;
  isAdding: boolean;
}

function AddUserForm({ onAddUser, isAdding }: AddUserFormProps) {
  const [username, setUsername] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<PermissionLevel>('read');
  const [error, setError] = useState<string | null>(null);
  const { t } = useTranslation(['collaboration', 'common']);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!username.trim()) {
      setError(t('collaboration:permissions.usernameRequired'));
      return;
    }

    onAddUser(username.trim(), selectedLevel);
    setUsername('');
    setSelectedLevel('read');
    setError(null);
  };

  return (
    <Card className="border-dashed">
      <CardContent className="p-4">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex items-start gap-2">
            <UserPlus className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div className="flex-1 space-y-3">
              <div>
                <Input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder={t('collaboration:permissions.enterUsername')}
                  disabled={isAdding}
                  className="text-sm"
                />
                {error && (
                  <p className="text-xs text-destructive mt-1">{error}</p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={selectedLevel}
                  onChange={(e) => setSelectedLevel(e.target.value as PermissionLevel)}
                  disabled={isAdding}
                  className="text-sm rounded-md border border-input bg-background px-2 py-1 flex-1"
                >
                  <option value="read">{t('collaboration:permissions.read')}</option>
                  <option value="write">{t('collaboration:permissions.write')}</option>
                  <option value="admin">{t('collaboration:permissions.admin')}</option>
                </select>

                <Button
                  type="submit"
                  size="sm"
                  disabled={isAdding || !username.trim()}
                  className="gap-1"
                >
                  {isAdding ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {t('collaboration:permissions.adding')}
                    </>
                  ) : (
                    <>
                      <UserPlus className="h-3 w-3" />
                      {t('collaboration:permissions.addUser')}
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

/**
 * PermissionsPanel Component
 */
export function PermissionsPanel({
  specId,
  onPermissionGranted,
  onPermissionUpdated,
  onPermissionRevoked,
  className
}: PermissionsPanelProps) {
  const [permissions, setPermissions] = useState<SpecPermission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { t } = useTranslation(['collaboration', 'common']);

  // Load permissions when component mounts
  useEffect(() => {
    loadPermissions();
  }, [specId]);

  const loadPermissions = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call once handler is implemented
      // const result = await window.electronAPI.collaborationPermissionsGet(specId);
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to load permissions');
      // }
      // setPermissions(result.data || []);

      // Placeholder: Empty permissions until IPC handler is implemented
      setPermissions([]);
    } catch (err) {
      console.error('Failed to load permissions:', err);
      setError(err instanceof Error ? err.message : 'Failed to load permissions');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddUser = async (username: string, level: PermissionLevel) => {
    setIsAdding(true);
    setError(null);

    try {
      // TODO: Replace with actual IPC call
      // const result = await window.electronAPI.collaborationPermissionsAdd({
      //   specId,
      //   username,
      //   level
      // });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to add user');
      // }

      // Placeholder: Create mock permission
      const newPermission: SpecPermission = {
        spec_id: specId,
        user: {
          user_id: `user-${Date.now()}`,
          username,
          email: `${username}@example.com`
        },
        level,
        granted_by: 'current-user',
        granted_at: new Date().toISOString()
      };

      setPermissions(prev => [...prev, newPermission]);
      onPermissionGranted?.(newPermission);
    } catch (err) {
      console.error('Failed to add user:', err);
      setError(err instanceof Error ? err.message : 'Failed to add user');
    } finally {
      setIsAdding(false);
    }
  };

  const handleUpdatePermission = async (userId: string, level: PermissionLevel) => {
    setError(null);

    try {
      // TODO: Replace with actual IPC call
      // const result = await window.electronAPI.collaborationPermissionsUpdate({
      //   specId,
      //   userId,
      //   level
      // });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to update permission');
      // }

      // Placeholder: Update local state
      setPermissions(prev =>
        prev.map(p =>
          p.user.user_id === userId
            ? { ...p, level }
            : p
        )
      );

      const updatedPermission = permissions.find(p => p.user.user_id === userId);
      if (updatedPermission) {
        onPermissionUpdated?.({ ...updatedPermission, level });
      }
    } catch (err) {
      console.error('Failed to update permission:', err);
      setError(err instanceof Error ? err.message : 'Failed to update permission');
    }
  };

  const handleRevokePermission = async (userId: string) => {
    setError(null);

    try {
      // TODO: Replace with actual IPC call
      // const result = await window.electronAPI.collaborationPermissionsRemove({
      //   specId,
      //   userId
      // });
      // if (!result.success) {
      //   throw new Error(result.error || 'Failed to remove user');
      // }

      // Placeholder: Update local state
      setPermissions(prev => prev.filter(p => p.user.user_id !== userId));
      onPermissionRevoked?.(userId);
    } catch (err) {
      console.error('Failed to remove user:', err);
      setError(err instanceof Error ? err.message : 'Failed to remove user');
    }
  };

  const permissionCounts = {
    read: permissions.filter(p => p.level === 'read').length,
    write: permissions.filter(p => p.level === 'write').length,
    admin: permissions.filter(p => p.level === 'admin').length
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            {t('collaboration:permissions.title')}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {t('collaboration:permissions.description')}
          </p>
        </div>
        {permissions.length > 0 && (
          <div className="flex items-center gap-2 text-xs">
            <Badge variant="outline" className="bg-blue-500/10 text-blue-500 border-blue-500/20">
              {permissionCounts.read} {t('collaboration:permissions.readBadge')}
            </Badge>
            <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
              {permissionCounts.write} {t('collaboration:permissions.writeBadge')}
            </Badge>
            <Badge variant="outline" className="bg-purple-500/10 text-purple-500 border-purple-500/20">
              {permissionCounts.admin} {t('collaboration:permissions.adminBadge')}
            </Badge>
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-center gap-3 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>{t('collaboration:permissions.loading')}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="p-4">
            <div className="flex items-start gap-3 text-destructive">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">{t('collaboration:permissions.error')}</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add User Form */}
      {!isLoading && (
        <AddUserForm onAddUser={handleAddUser} isAdding={isAdding} />
      )}

      {/* Permissions List */}
      {!isLoading && permissions.length > 0 && (
        <div className="space-y-3">
          {permissions.map((permission) => (
            <PermissionCard
              key={permission.user.user_id}
              permission={permission}
              canEdit={true} // TODO: Check if current user has admin permission
              onUpdate={handleUpdatePermission}
              onRemove={handleRevokePermission}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && permissions.length === 0 && !error && (
        <Card>
          <CardContent className="p-8">
            <div className="flex flex-col items-center gap-3 text-center text-muted-foreground">
              <Shield className="h-10 w-10 opacity-20" />
              <p className="text-sm">{t('collaboration:permissions.noMembers')}</p>
              <p className="text-xs">{t('collaboration:permissions.addMembersPrompt')}</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
