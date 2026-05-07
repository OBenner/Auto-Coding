import {
  CheckCircle2,
  Rocket,
  FileText,
  Settings,
  BookOpen,
  ArrowRight,
  AlertTriangle,
  Loader2
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { useSettingsStore } from '../../stores/settings-store';
import { useClaudeProfileStore } from '../../stores/claude-profile-store';

interface CompletionStepProps {
  authRuntime?: 'anthropic' | 'codex';
  onFinish: () => void;
  onOpenTaskCreator?: () => void;
  onOpenSettings?: () => void;
}

interface NextStepCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: () => void;
  actionLabel?: string;
}

function NextStepCard({ icon, title, description, action, actionLabel }: NextStepCardProps) {
  return (
    <Card className="border border-border bg-card/50 backdrop-blur-sm">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-foreground">{title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
            {action && actionLabel && (
              <Button
                variant="link"
                size="sm"
                onClick={action}
                className="mt-2 h-auto p-0 text-primary hover:text-primary/80"
              >
                {actionLabel}
                <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

type ReadinessState = 'checking' | 'ready' | 'warning' | 'skipped';

interface ReadinessItem {
  id: string;
  state: ReadinessState;
  label: string;
}

function ReadinessRow({ item }: { item: ReadinessItem }) {
  const icon =
    item.state === 'checking' ? (
      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
    ) : item.state === 'ready' || item.state === 'skipped' ? (
      <CheckCircle2 className="h-4 w-4 text-success" />
    ) : (
      <AlertTriangle className="h-4 w-4 text-warning" />
    );

  return (
    <div className="flex items-center gap-3 rounded-md border border-border/60 px-3 py-2">
      {icon}
      <span className="text-sm text-foreground">{item.label}</span>
    </div>
  );
}

function isCodexProfileAuthenticated(profile: unknown): boolean {
  if (!profile || typeof profile !== 'object') return false;
  const candidate = profile as {
    authenticated?: boolean;
    isAuthenticated?: boolean;
    configDir?: string;
  };
  return Boolean(candidate.authenticated || candidate.isAuthenticated || candidate.configDir);
}

function CompletionReadiness({ authRuntime }: { authRuntime: 'anthropic' | 'codex' }) {
  const { t } = useTranslation('onboarding');
  const { settings, profiles: apiProfiles } = useSettingsStore();
  const { profiles: claudeProfiles } = useClaudeProfileStore();
  const [items, setItems] = useState<ReadinessItem[]>([
    {
      id: 'auth',
      state: 'checking',
      label: t(
        authRuntime === 'codex'
          ? 'completion.readiness.codexAuth.checking'
          : 'completion.readiness.claudeAuth.checking'
      )
    },
    {
      id: 'cli',
      state: 'checking',
      label: t(
        authRuntime === 'codex'
          ? 'completion.readiness.codexCli.checking'
          : 'completion.readiness.claudeCli.checking'
      )
    },
    {
      id: 'memory',
      state: settings.memoryEnabled === false ? 'skipped' : 'checking',
      label: t(
        settings.memoryEnabled === false
          ? 'completion.readiness.memory.skipped'
          : 'completion.readiness.memory.checking'
      )
    }
  ]);

  useEffect(() => {
    let cancelled = false;

    const runChecks = async () => {
      const nextItems: ReadinessItem[] = [];

      if (authRuntime === 'codex') {
        try {
          const result = await window.electronAPI.getCodexProfiles();
          const profiles = result.success && result.data ? result.data.profiles : [];
          const hasCodexAuth = profiles.some(isCodexProfileAuthenticated);
          nextItems.push({
            id: 'auth',
            state: hasCodexAuth ? 'ready' : 'warning',
            label: t(
              hasCodexAuth
                ? 'completion.readiness.codexAuth.ready'
                : 'completion.readiness.codexAuth.issue'
            )
          });
        } catch {
          nextItems.push({
            id: 'auth',
            state: 'warning',
            label: t('completion.readiness.codexAuth.issue')
          });
        }

        try {
          const result = await window.electronAPI.checkCodexCodeVersion();
          const installed = Boolean(result.success && result.data?.installed);
          nextItems.push({
            id: 'cli',
            state: installed ? 'ready' : 'warning',
            label: t(
              installed
                ? 'completion.readiness.codexCli.ready'
                : 'completion.readiness.codexCli.issue'
            )
          });
        } catch {
          nextItems.push({
            id: 'cli',
            state: 'warning',
            label: t('completion.readiness.codexCli.issue')
          });
        }
      } else {
        const hasApiProfile = apiProfiles.length > 0;
        const hasClaudeProfile = claudeProfiles.some((profile) =>
          Boolean(profile.oauthToken || profile.configDir)
        );
        const hasClaudeAuth = hasApiProfile || hasClaudeProfile;

        nextItems.push({
          id: 'auth',
          state: hasClaudeAuth ? 'ready' : 'warning',
          label: t(
            hasClaudeAuth
              ? 'completion.readiness.claudeAuth.ready'
              : 'completion.readiness.claudeAuth.issue'
          )
        });

        try {
          const result = await window.electronAPI.checkClaudeCodeVersion();
          const installed = Boolean(result.success && result.data?.installed);
          nextItems.push({
            id: 'cli',
            state: installed ? 'ready' : 'warning',
            label: t(
              installed
                ? 'completion.readiness.claudeCli.ready'
                : 'completion.readiness.claudeCli.issue'
            )
          });
        } catch {
          nextItems.push({
            id: 'cli',
            state: 'warning',
            label: t('completion.readiness.claudeCli.issue')
          });
        }
      }

      if (settings.memoryEnabled === false) {
        nextItems.push({
          id: 'memory',
          state: 'skipped',
          label: t('completion.readiness.memory.skipped')
        });
      } else {
        try {
          const result = await window.electronAPI.getMemoryInfrastructureStatus();
          const ready = Boolean(result.success && result.data?.ready);
          nextItems.push({
            id: 'memory',
            state: ready ? 'ready' : 'warning',
            label: t(
              ready
                ? 'completion.readiness.memory.ready'
                : 'completion.readiness.memory.issue'
            )
          });
        } catch {
          nextItems.push({
            id: 'memory',
            state: 'warning',
            label: t('completion.readiness.memory.issue')
          });
        }
      }

      if (!cancelled) {
        setItems(nextItems);
      }
    };

    runChecks();

    return () => {
      cancelled = true;
    };
  }, [apiProfiles, authRuntime, claudeProfiles, settings.memoryEnabled, t]);

  return (
    <Card className="border border-border bg-card/50 mb-8">
      <CardContent className="p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <CheckCircle2 className="h-4 w-4" />
          {t('completion.readiness.title')}
        </div>
        <div className="grid grid-cols-1 gap-2">
          {items.map((item) => (
            <ReadinessRow key={item.id} item={item} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Completion step component for the onboarding wizard.
 * Displays a success message with suggestions for next steps
 * and a prominent "Finish" button to complete the wizard.
 */
export function CompletionStep({
  authRuntime = 'anthropic',
  onFinish,
  onOpenTaskCreator,
  onOpenSettings
}: CompletionStepProps) {
  const { t } = useTranslation('onboarding');

  const nextSteps = [
    {
      icon: <FileText className="h-5 w-5" />,
      title: t('completion.createTask.title'),
      description: t('completion.createTask.description'),
      action: onOpenTaskCreator,
      actionLabel: t('completion.createTask.action')
    },
    {
      icon: <Settings className="h-5 w-5" />,
      title: t('completion.customizeSettings.title'),
      description: t('completion.customizeSettings.description'),
      action: onOpenSettings,
      actionLabel: t('completion.customizeSettings.action')
    },
    {
      icon: <BookOpen className="h-5 w-5" />,
      title: t('completion.exploreDocs.title'),
      description: t('completion.exploreDocs.description')
    }
  ];

  return (
    <div className="flex h-full flex-col items-center justify-center px-8 py-6">
      <div className="w-full max-w-2xl">
        {/* Success Hero */}
        <div className="text-center mb-10">
          <div className="flex justify-center mb-6">
            <div className="relative">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-success/20 text-success">
                <CheckCircle2 className="h-10 w-10" />
              </div>
              <div className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <Rocket className="h-4 w-4" />
              </div>
            </div>
          </div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">
            {t('completion.title')}
          </h1>
          <p className="mt-3 text-muted-foreground text-lg">
            {t('completion.subtitle')}
          </p>
        </div>

        {/* Completion message */}
        <Card className="border border-success/30 bg-success/10 mb-8">
          <CardContent className="p-5">
            <div className="flex items-start gap-4">
              <CheckCircle2 className="h-6 w-6 text-success shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="text-lg font-medium text-success">
                  {t('completion.setupComplete')}
                </h3>
                <p className="mt-1 text-sm text-success/80">
                  {t('completion.setupCompleteDescription')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <CompletionReadiness authRuntime={authRuntime} />

        {/* Next Steps Section */}
        <div className="space-y-4 mb-10">
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Rocket className="h-4 w-4" />
            {t('completion.whatsNext')}
          </div>
          <div className="grid grid-cols-1 gap-3">
            {nextSteps.map((step, index) => (
              <NextStepCard
                // biome-ignore lint/suspicious/noArrayIndexKey: Static list with stable order
                key={index}
                icon={step.icon}
                title={step.title}
                description={step.description}
                action={step.action}
                actionLabel={step.actionLabel}
              />
            ))}
          </div>
        </div>

        {/* Finish Button */}
        <div className="flex flex-col items-center gap-4">
          <Button
            size="lg"
            onClick={onFinish}
            className="gap-2 px-10"
          >
            <Rocket className="h-5 w-5" />
            {t('completion.finish')}
          </Button>
          <p className="text-sm text-muted-foreground text-center">
            {t('completion.rerunHint')}
          </p>
        </div>
      </div>
    </div>
  );
}
