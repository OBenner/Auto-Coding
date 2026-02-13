/**
 * SecuritySettings - Security configuration management
 *
 * Provides user-friendly interface for configuring security settings including:
 * - Command allowlist management
 * - Filesystem permissions
 * - Security level presets (paranoid, standard, permissive)
 * - Security audit logs
 * - Security configuration export
 *
 * This component serves as the main container for security-related settings.
 */
import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Shield,
  AlertTriangle,
  Download,
  RefreshCw,
  Loader2,
  FileText,
  Check,
  AlertCircle
} from 'lucide-react';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { SettingsSection } from './SettingsSection';
import { useToast } from '../../hooks/use-toast';
import { useSettingsStore } from '../../stores/settings-store';
import type { AppSettings } from '../../../shared/types';
import type { SecurityProfile, SecurityAuditLog, SecurityLevel } from '../../../shared/types/security';

export interface SecurityLevelPreset {
  level: SecurityLevel;
  nameKey: string;
  descriptionKey: string;
  riskLevel: 'high' | 'medium' | 'low';
  allowlistSize: number;
  filesystemRestrictions: boolean;
  apiRestrictions: boolean;
}

// Security level presets configuration
const SECURITY_LEVEL_PRESETS: SecurityLevelPreset[] = [
  {
    level: 'paranoid',
    nameKey: 'security.levels.paranoid.name',
    descriptionKey: 'security.levels.paranoid.description',
    riskLevel: 'low',
    allowlistSize: 10,
    filesystemRestrictions: true,
    apiRestrictions: true
  },
  {
    level: 'standard',
    nameKey: 'security.levels.standard.name',
    descriptionKey: 'security.levels.standard.description',
    riskLevel: 'medium',
    allowlistSize: 50,
    filesystemRestrictions: false,
    apiRestrictions: false
  },
  {
    level: 'permissive',
    nameKey: 'security.levels.permissive.name',
    descriptionKey: 'security.levels.permissive.description',
    riskLevel: 'high',
    allowlistSize: 100,
    filesystemRestrictions: false,
    apiRestrictions: false
  }
];

interface SecuritySettingsProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
  isOpen: boolean;
}

/**
 * Main security settings component
 */
export function SecuritySettings({ settings, onSettingsChange, isOpen }: SecuritySettingsProps) {
  const { t } = useTranslation('security');
  const { t: tCommon } = useTranslation('common');
  const { toast } = useToast();

  // Security profile state
  const [securityProfile, setSecurityProfile] = useState<SecurityProfile | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Audit log state
  const [auditLogs, setAuditLogs] = useState<SecurityAuditLog[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const [logCount, setLogCount] = useState<number>(0);

  // Export state
  const [isExporting, setIsExporting] = useState(false);

  // Current security level
  const [currentLevel, setCurrentLevel] = useState<SecurityLevel>('standard');

  // Warning state for risky changes
  const [warningDialog, setWarningDialog] = useState<{
    show: boolean;
    message: string;
    onConfirm: () => void;
  }>({
    show: false,
    message: '',
    onConfirm: () => {}
  });

  // Load security profile when section opens
  useEffect(() => {
    if (isOpen) {
      loadSecurityProfile();
      loadAuditLogs();
    }
  }, [isOpen]);

  /**
   * Load security profile from backend
   */
  const loadSecurityProfile = async () => {
    setIsLoadingProfile(true);
    try {
      const result = await window.electronAPI.getSecurityProfile?.();
      if (result?.success && result.data) {
        setSecurityProfile(result.data);
        // Determine current level based on profile settings
        const detectedLevel = detectSecurityLevel(result.data);
        setCurrentLevel(detectedLevel);
      }
    } catch (err) {
      console.warn('[SecuritySettings] Failed to load security profile:', err);
      toast({
        variant: 'destructive',
        title: t('toast.loadProfileFailed'),
        description: tCommon('tryAgain'),
      });
    } finally {
      setIsLoadingProfile(false);
    }
  };

  /**
   * Load audit logs from backend
   */
  const loadAuditLogs = async () => {
    setIsLoadingLogs(true);
    try {
      const result = await window.electronAPI.getSecurityAuditLogs?.();
      if (result?.success && result.data) {
        setAuditLogs(result.data.logs || []);
        setLogCount(result.data.totalCount || 0);
      }
    } catch (err) {
      console.warn('[SecuritySettings] Failed to load audit logs:', err);
    } finally {
      setIsLoadingLogs(false);
    }
  };

  /**
   * Detect security level based on profile settings
   */
  const detectSecurityLevel = (profile: SecurityProfile): SecurityLevel => {
    if (profile.filesystemRestricted && profile.apiRestricted && profile.commandAllowlist.length <= 15) {
      return 'paranoid';
    }
    if (!profile.filesystemRestricted && !profile.apiRestricted && profile.commandAllowlist.length > 75) {
      return 'permissive';
    }
    return 'standard';
  };

  /**
   * Apply security level preset
   */
  const applySecurityLevel = async (level: SecurityLevel) => {
    const preset = SECURITY_LEVEL_PRESETS.find(p => p.level === level);
    if (!preset || !securityProfile) return;

    // Show warning for risky changes
    if (preset.riskLevel === 'high') {
      setWarningDialog({
        show: true,
        message: t('warnings.permissiveLevel'),
        onConfirm: () => {
          setWarningDialog({ show: false, message: '', onConfirm: () => {} });
          applyLevelPreset(preset);
        }
      });
      return;
    }

    await applyLevelPreset(preset);
  };

  /**
   * Apply the actual preset changes
   */
  const applyLevelPreset = async (preset: SecurityLevelPreset) => {
    if (!securityProfile) return;

    setIsSavingProfile(true);
    try {
      const updatedProfile: SecurityProfile = {
        ...securityProfile,
        filesystemRestricted: preset.filesystemRestrictions,
        apiRestricted: preset.apiRestrictions,
        commandAllowlist: securityProfile.commandAllowlist.slice(0, preset.allowlistSize)
      };

      const result = await window.electronAPI.updateSecurityProfile?.(updatedProfile);
      if (result?.success) {
        setSecurityProfile(updatedProfile);
        setCurrentLevel(preset.level);
        toast({
          title: t('toast.levelApplied'),
          description: t(`toast.levelApplied.${preset.level}`),
        });
      } else {
        toast({
          variant: 'destructive',
          title: t('toast.saveProfileFailed'),
          description: result?.error || tCommon('tryAgain'),
        });
      }
    } catch (err) {
      console.warn('[SecuritySettings] Failed to apply security level:', err);
      toast({
        variant: 'destructive',
        title: t('toast.saveProfileFailed'),
        description: tCommon('tryAgain'),
      });
    } finally {
      setIsSavingProfile(false);
    }
  };

  /**
   * Export security configuration
   */
  const exportSecurityConfig = async () => {
    setIsExporting(true);
    try {
      const result = await window.electronAPI.exportSecurityConfig?.();
      if (result?.success) {
        toast({
          title: t('toast.exportSuccess'),
          description: t('toast.exportSuccessDescription'),
        });
      } else {
        toast({
          variant: 'destructive',
          title: t('toast.exportFailed'),
          description: result?.error || tCommon('tryAgain'),
        });
      }
    } catch (err) {
      console.warn('[SecuritySettings] Failed to export config:', err);
      toast({
        variant: 'destructive',
        title: t('toast.exportFailed'),
        description: tCommon('tryAgain'),
      });
    } finally {
      setIsExporting(false);
    }
  };

  /**
   * Refresh audit logs
   */
  const refreshAuditLogs = async () => {
    await loadAuditLogs();
    toast({
      title: t('toast.logsRefreshed'),
      description: t('toast.logsRefreshedDescription'),
    });
  };

  return (
    <SettingsSection
      title={t('title')}
      description={t('description')}
    >
      <div className="space-y-6">
        {/* Security Level Selection */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-semibold text-foreground">{t('levels.title')}</h3>
          </div>

          {isLoadingProfile ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-3">
              {SECURITY_LEVEL_PRESETS.map((preset) => (
                <div
                  key={preset.level}
                  className={`p-4 rounded-lg border transition-all cursor-pointer ${
                    currentLevel === preset.level
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:bg-accent/50'
                  }`}
                  onClick={() => currentLevel !== preset.level && !isSavingProfile && applySecurityLevel(preset.level)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Label className="text-base font-medium text-foreground">
                          {t(preset.nameKey)}
                        </Label>
                        {currentLevel === preset.level && (
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            preset.riskLevel === 'low' ? 'bg-success/20 text-success' :
                            preset.riskLevel === 'medium' ? 'bg-warning/20 text-warning' :
                            'bg-destructive/20 text-destructive'
                          }`}>
                            {t('status.active')}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        {t(preset.descriptionKey)}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{t('levels.maxCommands', { count: preset.allowlistSize })}</span>
                        <span>•</span>
                        <span>{preset.filesystemRestrictions ? t('levels.filesystemRestricted') : t('levels.filesystemOpen')}</span>
                        <span>•</span>
                        <span>{preset.apiRestrictions ? t('levels.apiRestricted') : t('levels.apiOpen')}</span>
                      </div>
                    </div>
                    {currentLevel === preset.level ? (
                      <Check className="h-5 w-5 text-primary shrink-0" />
                    ) : isSavingProfile ? (
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground shrink-0" />
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Security Profile Summary */}
        {securityProfile && (
          <div className="space-y-4 pt-4 border-t border-border">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-muted-foreground" />
              <h3 className="text-lg font-semibold text-foreground">{t('profile.title')}</h3>
            </div>

            <div className="rounded-lg bg-muted/30 border border-border p-4 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{t('profile.totalCommands')}</span>
                <span className="font-mono font-medium text-foreground">{securityProfile.commandAllowlist.length}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{t('profile.filesystemAccess')}</span>
                <span className={`font-medium ${
                  securityProfile.filesystemRestricted ? 'text-warning' : 'text-success'
                }`}>
                  {securityProfile.filesystemRestricted ? t('profile.restricted') : t('profile.fullAccess')}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{t('profile.apiAccess')}</span>
                <span className={`font-medium ${
                  securityProfile.apiRestricted ? 'text-warning' : 'text-success'
                }`}>
                  {securityProfile.apiRestricted ? t('profile.restricted') : t('profile.fullAccess')}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={exportSecurityConfig}
                disabled={isExporting}
              >
                {isExporting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('actions.exporting')}
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    {t('actions.export')}
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Audit Log Summary */}
        <div className="space-y-4 pt-4 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-muted-foreground" />
              <h3 className="text-lg font-semibold text-foreground">{t('audit.title')}</h3>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={refreshAuditLogs}
              disabled={isLoadingLogs}
            >
              {isLoadingLogs ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          </div>

          <div className="rounded-lg bg-muted/30 border border-border p-4">
            <div className="flex items-center justify-between text-sm mb-3">
              <span className="text-muted-foreground">{t('audit.totalEvents')}</span>
              <span className="font-mono font-medium text-foreground">{logCount}</span>
            </div>

            {/* Recent events preview (show last 3) */}
            {auditLogs.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground mb-2">{t('audit.recentEvents')}</p>
                {auditLogs.slice(0, 3).map((log) => (
                  <div key={log.id} className="text-xs flex items-center justify-between py-2 border-t border-border/50">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${
                        log.severity === 'high' ? 'bg-destructive' :
                        log.severity === 'medium' ? 'bg-warning' :
                        'bg-success'
                      }`} />
                      <span className="text-foreground">{log.operation}</span>
                    </div>
                    <span className="text-muted-foreground">{new Date(log.timestamp).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}

            {auditLogs.length === 0 && !isLoadingLogs && (
              <p className="text-sm text-muted-foreground text-center py-2">
                {t('audit.noEvents')}
              </p>
            )}
          </div>
        </div>

        {/* Security Warning Banner */}
        {currentLevel === 'permissive' && (
          <div className="rounded-lg border-2 border-warning/50 bg-warning/5 p-4 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-warning mb-1">{t('warnings.riskyConfigTitle')}</p>
              <p className="text-xs text-muted-foreground">{t('warnings.riskyConfigDescription')}</p>
            </div>
          </div>
        )}
      </div>

      {/* Warning Dialog */}
      {warningDialog.show && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background border border-border rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-start gap-3 mb-4">
              <AlertTriangle className="h-6 w-6 text-warning shrink-0" />
              <div>
                <h4 className="font-semibold text-foreground mb-2">{t('warnings.dialogTitle')}</h4>
                <p className="text-sm text-muted-foreground">{warningDialog.message}</p>
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setWarningDialog({ show: false, message: '', onConfirm: () => {} })}
              >
                {tCommon('buttons.cancel')}
              </Button>
              <Button
                variant="destructive"
                onClick={warningDialog.onConfirm}
              >
                {t('warnings.confirmRisk')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </SettingsSection>
  );
}
