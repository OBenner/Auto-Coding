import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Webhook,
  Plus,
  Trash2,
  Edit2,
  Play,
  Save,
  X,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from './ui/select';
import { Checkbox } from './ui/checkbox';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from './ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from './ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Badge } from './ui/badge';
import { useWebhookStore, loadWebhooks, loadWebhookMetadata } from '../stores/webhook-store';
import type {
  WebhookConfig,
  WebhookEventType,
  WebhookTemplate,
  WebhookEventTypeMeta,
  WebhookTemplateMeta,
  WebhookRetryConfig
} from '../../shared/types/webhook';

interface WebhooksPageProps {
  projectId: string;
}

interface WebhookForm {
  name: string;
  url: string;
  secret: string;
  events: WebhookEventType[];
  template: WebhookTemplate;
  enabled: boolean;
  headers: Record<string, string>;
  retry_config: WebhookRetryConfig;
}

const emptyForm: WebhookForm = {
  name: '',
  url: '',
  secret: '',
  events: [],
  template: 'generic',
  enabled: true,
  headers: {},
  retry_config: {
    max_retries: 3,
    initial_delay: 1.0,
    max_delay: 60.0,
    backoff_multiplier: 2.0
  }
};

export function WebhooksPage({ projectId }: WebhooksPageProps) {
  const { t } = useTranslation(['webhooks', 'common']);

  // Store state
  const {
    webhooks,
    webhooksLoading,
    webhooksError,
    deliveries,
    deliveriesLoading,
    stats,
    statsLoading,
    isTestingWebhook,
    testResult,
    eventTypes,
    templates
  } = useWebhookStore();

  // Local state
  const [activeTab, setActiveTab] = useState('webhooks');
  const [showDialog, setShowDialog] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<WebhookConfig | null>(null);
  const [formData, setFormData] = useState<WebhookForm>(emptyForm);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [selectedWebhookId, setSelectedWebhookId] = useState<string | null>(null);

  // Load data on mount
  useEffect(() => {
    loadWebhooks(projectId);
    loadWebhookMetadata();
  }, [projectId]);

  // Handle opening dialog for new webhook
  const handleAddWebhook = () => {
    setEditingWebhook(null);
    setFormData({ ...emptyForm, events: ['*'] });
    setFormErrors({});
    setShowDialog(true);
  };

  // Handle opening dialog for editing webhook
  const handleEditWebhook = (webhook: WebhookConfig) => {
    setEditingWebhook(webhook);
    setFormData({
      name: webhook.name,
      url: webhook.url,
      secret: webhook.secret || '',
      events: webhook.events,
      template: webhook.template,
      enabled: webhook.enabled,
      headers: { ...webhook.headers },
      retry_config: { ...webhook.retry_config }
    });
    setFormErrors({});
    setShowDialog(true);
  };

  // Handle closing dialog
  const handleCloseDialog = () => {
    setShowDialog(false);
    setEditingWebhook(null);
    setFormData(emptyForm);
    setFormErrors({});
  };

  // Validate form
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = t('webhooks:errors.nameRequired');
    }

    if (!formData.url.trim()) {
      errors.url = t('webhooks:errors.urlRequired');
    } else {
      try {
        new URL(formData.url);
      } catch {
        errors.url = t('webhooks:errors.urlInvalid');
      }
    }

    if (formData.events.length === 0) {
      errors.events = t('webhooks:errors.eventsRequired');
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle saving webhook
  const handleSaveWebhook = async () => {
    if (!validateForm()) {
      return;
    }

    const { saveWebhook, updateWebhook } = useWebhookStore.getState();

    if (editingWebhook) {
      await updateWebhook(projectId, editingWebhook.webhook_id, formData);
    } else {
      await saveWebhook(projectId, formData);
    }

    handleCloseDialog();
  };

  // Handle deleting webhook
  const handleDeleteWebhook = async (webhook: WebhookConfig) => {
    if (!confirm(t('webhooks:confirmDelete'))) {
      return;
    }

    const { deleteWebhook } = useWebhookStore.getState();
    await deleteWebhook(projectId, webhook.webhook_id);
  };

  // Handle testing webhook
  const handleTestWebhook = async (webhook: WebhookConfig) => {
    setSelectedWebhookId(webhook.webhook_id);
    const { testWebhook } = useWebhookStore.getState();
    await testWebhook(projectId, webhook.webhook_id);
  };

  // Handle form field changes
  const handleFormFieldChange = (field: keyof WebhookForm, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (formErrors[field]) {
      setFormErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  // Handle event type toggle
  const handleEventToggle = (eventType: WebhookEventType) => {
    setFormData((prev) => {
      if (eventType === '*') {
        return { ...prev, events: ['*'] };
      }

      const currentEvents = prev.events.includes('*') ? [] : prev.events;
      const isSelected = currentEvents.includes(eventType);

      if (isSelected) {
        return { ...prev, events: currentEvents.filter((e) => e !== eventType) };
      } else {
        return { ...prev, events: [...currentEvents, eventType] };
      }
    });
  };

  // Get event label
  const getEventLabel = (eventType: string): string => {
    const meta = eventTypes.find((e) => e.value === eventType);
    return meta?.label || eventType;
  };

  // Get template label
  const getTemplateLabel = (template: WebhookTemplate): string => {
    const meta = templates.find((t) => t.value === template);
    return meta?.label || template;
  };

  // Render webhook card
  const renderWebhookCard = (webhook: WebhookConfig) => (
    <Card key={webhook.webhook_id}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg">{webhook.name}</CardTitle>
              {!webhook.enabled && (
                <Badge variant="secondary">{t('webhooks:status.disabled')}</Badge>
              )}
              {testResult?.webhook_id === webhook.webhook_id && testResult && (
                testResult.success ? (
                  <Badge variant="default" className="gap-1">
                    <CheckCircle className="h-3 w-3" />
                    {t('webhooks:test.success')}
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="gap-1">
                    <XCircle className="h-3 w-3" />
                    {t('webhooks:test.failed')}
                  </Badge>
                )
              )}
            </div>
            <CardDescription className="mt-1">{webhook.url}</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleTestWebhook(webhook)}
              disabled={isTestingWebhook && selectedWebhookId === webhook.webhook_id}
            >
              {isTestingWebhook && selectedWebhookId === webhook.webhook_id ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </Button>
            <Button variant="ghost" size="icon" onClick={() => handleEditWebhook(webhook)}>
              <Edit2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleDeleteWebhook(webhook)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium">{t('webhooks:form.template')}:</span>
            <span>{getTemplateLabel(webhook.template)}</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {webhook.events.map((event) => (
              <Badge key={event} variant="outline">
                {getEventLabel(event)}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  // Render webhook form dialog
  const renderWebhookDialog = () => (
    <Dialog open={showDialog} onOpenChange={setShowDialog}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {editingWebhook ? t('webhooks:dialog.editTitle') : t('webhooks:dialog.createTitle')}
          </DialogTitle>
          <DialogDescription>
            {editingWebhook ? t('webhooks:dialog.editDescription') : t('webhooks:dialog.createDescription')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">{t('webhooks:form.name')}</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleFormFieldChange('name', e.target.value)}
              placeholder={t('webhooks:form.namePlaceholder')}
            />
            {formErrors.name && (
              <p className="text-sm text-destructive">{formErrors.name}</p>
            )}
          </div>

          {/* URL */}
          <div className="space-y-2">
            <Label htmlFor="url">{t('webhooks:form.url')}</Label>
            <Input
              id="url"
              type="url"
              value={formData.url}
              onChange={(e) => handleFormFieldChange('url', e.target.value)}
              placeholder="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
            />
            {formErrors.url && (
              <p className="text-sm text-destructive">{formErrors.url}</p>
            )}
          </div>

          {/* Secret */}
          <div className="space-y-2">
            <Label htmlFor="secret">{t('webhooks:form.secret')}</Label>
            <Input
              id="secret"
              type="password"
              value={formData.secret}
              onChange={(e) => handleFormFieldChange('secret', e.target.value)}
              placeholder={t('webhooks:form.secretPlaceholder')}
            />
            <p className="text-sm text-muted-foreground">
              {t('webhooks:form.secretHint')}
            </p>
          </div>

          {/* Template */}
          <div className="space-y-2">
            <Label htmlFor="template">{t('webhooks:form.template')}</Label>
            <Select
              value={formData.template}
              onValueChange={(value) => handleFormFieldChange('template', value as WebhookTemplate)}
            >
              <SelectTrigger id="template">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {templates.map((template) => (
                  <SelectItem key={template.value} value={template.value}>
                    {template.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Events */}
          <div className="space-y-2">
            <Label>{t('webhooks:form.events')}</Label>
            {formErrors.events && (
              <p className="text-sm text-destructive">{formErrors.events}</p>
            )}
            <div className="space-y-2 border rounded-md p-3">
              {/* Wildcard option */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="event-*"
                  checked={formData.events.includes('*')}
                  onCheckedChange={() => handleEventToggle('*')}
                />
                <Label htmlFor="event-*" className="cursor-pointer">
                  {t('webhooks:events.all')}
                </Label>
              </div>
              <div className="h-px bg-border" />
              {/* Individual events */}
              {eventTypes.map((eventType) => (
                <div key={eventType.value} className="flex items-center space-x-2">
                  <Checkbox
                    id={`event-${eventType.value}`}
                    checked={formData.events.includes(eventType.value as WebhookEventType)}
                    onCheckedChange={() => handleEventToggle(eventType.value as WebhookEventType)}
                    disabled={formData.events.includes('*')}
                  />
                  <Label
                    htmlFor={`event-${eventType.value}`}
                    className="cursor-pointer flex-1"
                  >
                    <span>{eventType.label}</span>
                    <span className="text-muted-foreground text-xs ml-2">
                      {eventType.description}
                    </span>
                  </Label>
                </div>
              ))}
            </div>
          </div>

          {/* Enabled */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="enabled"
              checked={formData.enabled}
              onCheckedChange={(checked) =>
                handleFormFieldChange('enabled', checked as boolean)
              }
            />
            <Label htmlFor="enabled" className="cursor-pointer">
              {t('webhooks:form.enabled')}
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCloseDialog}>
            <X className="mr-2 h-4 w-4" />
            {t('common:buttons.cancel')}
          </Button>
          <Button onClick={handleSaveWebhook}>
            <Save className="mr-2 h-4 w-4" />
            {t('common:buttons.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );

  // Loading state
  if (webhooksLoading && webhooks.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (webhooksError) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h3 className="mt-4 text-lg font-semibold">{t('webhooks:error.title')}</h3>
          <p className="mt-2 text-sm text-muted-foreground">{webhooksError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">{t('webhooks:title')}</h1>
            <p className="text-sm text-muted-foreground mt-1">{t('webhooks:description')}</p>
          </div>
          <Button onClick={handleAddWebhook}>
            <Plus className="mr-2 h-4 w-4" />
            {t('webhooks:buttons.addWebhook')}
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
          <div className="border-b border-border px-6">
            <TabsList>
              <TabsTrigger value="webhooks">{t('webhooks:tabs.webhooks')}</TabsTrigger>
              <TabsTrigger value="history">{t('webhooks:tabs.history')}</TabsTrigger>
              <TabsTrigger value="stats">{t('webhooks:tabs.stats')}</TabsTrigger>
            </TabsList>
          </div>

          {/* Webhooks List Tab */}
          <TabsContent value="webhooks" className="flex-1 overflow-hidden m-0">
            <ScrollArea className="h-full">
              <div className="p-6 space-y-4">
                {webhooks.length === 0 ? (
                  <div className="text-center py-12">
                    <Webhook className="mx-auto h-12 w-12 text-muted-foreground" />
                    <h3 className="mt-4 text-lg font-semibold">{t('webhooks:empty.title')}</h3>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {t('webhooks:empty.description')}
                    </p>
                  </div>
                ) : (
                  webhooks.map(renderWebhookCard)
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Delivery History Tab */}
          <TabsContent value="history" className="flex-1 overflow-hidden m-0">
            <ScrollArea className="h-full">
              <div className="p-6">
                <div className="text-center py-12">
                  <Clock className="mx-auto h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">{t('webhooks:history.title')}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {t('webhooks:history.description')}
                  </p>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Statistics Tab */}
          <TabsContent value="stats" className="flex-1 overflow-hidden m-0">
            <ScrollArea className="h-full">
              <div className="p-6">
                <div className="text-center py-12">
                  <CheckCircle className="mx-auto h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">{t('webhooks:stats.title')}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {t('webhooks:stats.description')}
                  </p>
                </div>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>

      {/* Webhook Form Dialog */}
      {renderWebhookDialog()}
    </div>
  );
}
