import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Loader2,
  LogIn,
  Plus,
  Star,
  Trash2,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent } from '../ui/card';
import { cn } from '../../lib/utils';
import { AuthTerminal } from '../settings/AuthTerminal';
import { useToast } from '../../hooks/use-toast';
import type { CodexProfile } from '../../../shared/types';

interface CodexOAuthStepProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export function CodexOAuthStep({ onNext, onBack, onSkip }: CodexOAuthStepProps) {
  const { t } = useTranslation('onboarding');
  const { toast } = useToast();
  const [profiles, setProfiles] = useState<CodexProfile[]>([]);
  const [activeProfileId, setActiveProfileId] = useState<string | null>(null);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(true);
  const [newProfileName, setNewProfileName] = useState('');
  const [isAddingProfile, setIsAddingProfile] = useState(false);
  const [authenticatingProfileId, setAuthenticatingProfileId] = useState<string | null>(null);
  const [deletingProfileId, setDeletingProfileId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [authTerminal, setAuthTerminal] = useState<{
    terminalId: string;
    configDir: string;
    profileId: string;
    profileName: string;
  } | null>(null);

  const hasAuthenticatedProfile = profiles.some((profile) => profile.isAuthenticated);

  const loadProfiles = useCallback(async () => {
    setIsLoadingProfiles(true);
    setError(null);
    try {
      const result = await window.electronAPI.getCodexProfiles();
      if (result.success && result.data) {
        setProfiles(result.data.profiles);
        setActiveProfileId(result.data.activeProfileId);
      } else {
        setError(result.error || t('codexOauth.errors.loadProfiles'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('codexOauth.errors.loadProfiles'));
    } finally {
      setIsLoadingProfiles(false);
    }
  }, [t]);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  const startAuthentication = async (profile: CodexProfile) => {
    setAuthenticatingProfileId(profile.id);
    setError(null);
    try {
      const result = await window.electronAPI.authenticateCodexProfile(profile.id);
      if (!result.success || !result.data) {
        setError(result.error || t('codexOauth.errors.prepareAuth'));
        setAuthenticatingProfileId(null);
        return;
      }

      setAuthTerminal({
        terminalId: result.data.terminalId,
        configDir: result.data.configDir,
        profileId: profile.id,
        profileName: profile.name,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : t('codexOauth.errors.startAuth'));
      setAuthenticatingProfileId(null);
    }
  };

  const handleAddProfile = async () => {
    if (!newProfileName.trim()) return;

    setIsAddingProfile(true);
    setError(null);
    try {
      const name = newProfileName.trim();
      const result = await window.electronAPI.createCodexProfile(name);

      if (!result.success || !result.data) {
        setError(result.error || t('codexOauth.errors.addProfile'));
        return;
      }

      setNewProfileName('');
      await window.electronAPI.setActiveCodexProfile(result.data.id);
      await loadProfiles();
      await startAuthentication(result.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('codexOauth.errors.addProfile'));
    } finally {
      setIsAddingProfile(false);
    }
  };

  const handleSetActiveProfile = async (profileId: string) => {
    setError(null);
    try {
      const result = await window.electronAPI.setActiveCodexProfile(profileId);
      if (result.success) {
        setActiveProfileId(profileId);
      } else {
        setError(result.error || t('codexOauth.errors.setActiveProfile'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('codexOauth.errors.setActiveProfile'));
    }
  };

  const handleDeleteProfile = async (profileId: string) => {
    setDeletingProfileId(profileId);
    setError(null);
    try {
      const result = await window.electronAPI.deleteCodexProfile(profileId);
      if (!result.success) {
        setError(result.error || t('codexOauth.errors.deleteProfile'));
      }
      await loadProfiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('codexOauth.errors.deleteProfile'));
    } finally {
      setDeletingProfileId(null);
    }
  };

  const handleAuthTerminalClose = useCallback(async () => {
    setAuthTerminal(null);
    setAuthenticatingProfileId(null);
    await loadProfiles();
  }, [loadProfiles]);

  const handleAuthTerminalSuccess = useCallback(async () => {
    const profileId = authTerminal?.profileId;
    setAuthTerminal(null);
    setAuthenticatingProfileId(null);

    if (profileId) {
      await window.electronAPI.verifyCodexProfileAuth(profileId);
      await window.electronAPI.setActiveCodexProfile(profileId);
    }

    await loadProfiles();
    toast({
      title: t('codexOauth.toast.connectedTitle'),
      description: t('codexOauth.toast.connectedDescription'),
    });
  }, [authTerminal?.profileId, loadProfiles, t, toast]);

  const handleContinue = async () => {
    onNext();
  };

  return (
    <div className="flex h-full flex-col items-center justify-center px-8 py-6">
      <div className="w-full max-w-3xl">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <LogIn className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">
            {t('codexOauth.title')}
          </h1>
          <p className="mt-3 text-muted-foreground text-lg">
            {t('codexOauth.description')}
          </p>
        </div>

        <Card className="mb-6 border-border bg-card/50">
          <CardContent className="p-6 space-y-4">
            <div>
              <Label htmlFor="codex-profile-name">{t('codexOauth.labels.accountName')}</Label>
              <div className="mt-2 flex gap-2">
                <Input
                  id="codex-profile-name"
                  placeholder={t('codexOauth.labels.namePlaceholder')}
                  value={newProfileName}
                  onChange={(event) => setNewProfileName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      handleAddProfile();
                    }
                  }}
                />
                <Button onClick={handleAddProfile} disabled={!newProfileName.trim() || isAddingProfile}>
                  {isAddingProfile ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  {t('codexOauth.buttons.add')}
                </Button>
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {isLoadingProfiles ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('codexOauth.loadingProfiles')}
              </div>
            ) : (
              <div className="space-y-3">
                {profiles.map((profile) => {
                  const isActive = activeProfileId === profile.id;
                  const isAuthenticating = authenticatingProfileId === profile.id;

                  return (
                    <div
                      key={profile.id}
                      className={cn(
                        'flex items-center justify-between gap-4 rounded-md border p-4',
                        isActive ? 'border-primary/60 bg-primary/5' : 'border-border bg-background/40'
                      )}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium text-foreground">{profile.name}</span>
                          {profile.isDefault && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                              <Star className="h-3 w-3" />
                              {t('codexOauth.badges.default')}
                            </span>
                          )}
                          {isActive && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                              <Check className="h-3 w-3" />
                              {t('codexOauth.badges.active')}
                            </span>
                          )}
                          {profile.isAuthenticated ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-600">
                              <CheckCircle2 className="h-3 w-3" />
                              {t('codexOauth.badges.authenticated')}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-yellow-500/10 px-2 py-0.5 text-xs text-yellow-600">
                              <AlertCircle className="h-3 w-3" />
                              {t('codexOauth.badges.needsAuth')}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 truncate text-xs text-muted-foreground">{profile.email || profile.configDir}</p>
                      </div>

                      <div className="flex shrink-0 items-center gap-2">
                        {!isActive && (
                          <Button variant="outline" size="sm" onClick={() => handleSetActiveProfile(profile.id)}>
                            {t('codexOauth.buttons.setActive')}
                          </Button>
                        )}
                        <Button
                          variant={profile.isAuthenticated ? 'outline' : 'default'}
                          size="sm"
                          onClick={() => startAuthentication(profile)}
                          disabled={isAuthenticating}
                        >
                          {isAuthenticating ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogIn className="h-4 w-4" />}
                          {t('codexOauth.buttons.authenticate')}
                        </Button>
                        {!profile.isDefault && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteProfile(profile.id)}
                            disabled={deletingProfileId === profile.id}
                            aria-label={t('codexOauth.aria.deleteProfile')}
                          >
                            {deletingProfileId === profile.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-between">
          <Button variant="outline" onClick={onBack}>{t('codexOauth.buttons.back')}</Button>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onSkip}>{t('codexOauth.buttons.skip')}</Button>
            <Button onClick={handleContinue} disabled={!hasAuthenticatedProfile}>
              {t('codexOauth.buttons.continue')}
            </Button>
          </div>
        </div>
      </div>

      {authTerminal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-sm">
          <div className="h-[75vh] w-[90vw] max-w-5xl rounded-lg border bg-card shadow-xl">
            <AuthTerminal
              terminalId={authTerminal.terminalId}
              configDir={authTerminal.configDir}
              profileName={authTerminal.profileName}
              loginCommand="codex login"
              env={{ CODEX_HOME: authTerminal.configDir }}
              authProvider="codex"
              successOnExitCode
              onClose={handleAuthTerminalClose}
              onAuthSuccess={handleAuthTerminalSuccess}
              onAuthError={setError}
            />
          </div>
        </div>
      )}
    </div>
  );
}
