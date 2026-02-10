/**
 * TemplateWizard - Multi-step wizard for collecting template parameters
 *
 * Features:
 * - Dynamic form generation from template parameters
 * - Type-aware input fields (string, number, boolean, list, etc.)
 * - Validation with error messages
 * - Example parameter sets
 * - Preview before creation
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronRight, FileText, AlertCircle, Lightbulb } from 'lucide-react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { cn } from '../../lib/utils';
import type {
  Template,
  TemplateParameter,
  TemplateExample,
} from '../../../shared/types';

interface TemplateWizardProps {
  template: Template;
  onSubmit: (parameters: Record<string, unknown>) => void;
  onCancel: () => void;
  disabled?: boolean;
  initialValues?: Record<string, unknown>;
}

/**
 * Validate a parameter value based on its type and validation rules
 */
function validateParameter(
  value: unknown,
  param: TemplateParameter,
  t: (key: string, options?: Record<string, unknown>) => string
): string | null {
  // Check required
  if (param.required && (value === undefined || value === null || value === '')) {
    return t('templates:wizard.validation.required');
  }

  // Skip validation if value is empty and not required
  if (!param.required && (value === undefined || value === null || value === '')) {
    return null;
  }

  // Type-specific validation
  if (param.type === 'int' || param.type === 'float') {
    const numValue = typeof value === 'string' ? parseFloat(value) : Number(value);
    if (isNaN(numValue)) {
      return param.type === 'int'
        ? t('templates:wizard.validation.invalidInteger')
        : t('templates:wizard.validation.invalidNumber');
    }

    if (param.type === 'int' && !Number.isInteger(numValue)) {
      return t('templates:wizard.validation.invalidInteger');
    }

    if (param.validation?.min !== undefined && numValue < param.validation.min) {
      return t('templates:wizard.validation.minValue', { min: param.validation.min });
    }

    if (param.validation?.max !== undefined && numValue > param.validation.max) {
      return t('templates:wizard.validation.maxValue', { max: param.validation.max });
    }
  }

  // String pattern validation
  if (param.type === 'str' && param.validation?.pattern && typeof value === 'string') {
    const regex = new RegExp(param.validation.pattern);
    if (!regex.test(value)) {
      return t('templates:wizard.validation.patternMismatch');
    }
  }

  return null;
}

/**
 * Render input field based on parameter type
 */
function ParameterInput({
  name,
  param,
  value,
  onChange,
  error,
  disabled,
  t,
}: {
  name: string;
  param: TemplateParameter;
  value: unknown;
  onChange: (value: unknown) => void;
  error: string | null;
  disabled?: boolean;
  t: (key: string, options?: Record<string, unknown>) => string;
}) {
  const inputId = `param-${name}`;

  // Boolean type - checkbox
  if (param.type === 'bool') {
    return (
      <div className="flex items-center gap-3">
        <Checkbox
          id={inputId}
          checked={value === true}
          onCheckedChange={(checked) => onChange(checked === true)}
          disabled={disabled}
        />
        <Label htmlFor={inputId} className="text-sm font-normal cursor-pointer">
          {param.description}
        </Label>
      </div>
    );
  }

  // Enum/options type - select dropdown
  if (param.options && param.options.length > 0) {
    return (
      <Select
        value={value as string}
        onValueChange={onChange}
        disabled={disabled}
      >
        <SelectTrigger id={inputId} className={cn(error && 'border-destructive')}>
          <SelectValue placeholder={param.placeholder || t('templates:wizard.placeholder.string', { name })} />
        </SelectTrigger>
        <SelectContent>
          {param.options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  // List type - textarea (comma-separated)
  if (param.type === 'list') {
    const listValue = Array.isArray(value) ? value.join(', ') : (value as string) || '';
    return (
      <Textarea
        id={inputId}
        placeholder={param.placeholder || t('templates:wizard.placeholder.list')}
        value={listValue}
        onChange={(e) => {
          const text = e.target.value;
          const list = text.split(',').map((item) => item.trim()).filter((item) => item.length > 0);
          onChange(list);
        }}
        disabled={disabled}
        rows={3}
        className={cn(error && 'border-destructive')}
      />
    );
  }

  // Dict type - textarea (JSON)
  if (param.type === 'dict') {
    const dictValue = typeof value === 'object' && value !== null
      ? JSON.stringify(value, null, 2)
      : (value as string) || '';
    return (
      <Textarea
        id={inputId}
        placeholder={param.placeholder || '{\n  "key": "value"\n}'}
        value={dictValue}
        onChange={(e) => {
          const text = e.target.value;
          try {
            const parsed = JSON.parse(text);
            onChange(parsed);
          } catch {
            // Keep as string until valid JSON
            onChange(text);
          }
        }}
        disabled={disabled}
        rows={4}
        className={cn('font-mono text-xs', error && 'border-destructive')}
      />
    );
  }

  // Multi-line string - textarea
  if (param.type === 'str' && param.description.toLowerCase().includes('description')) {
    return (
      <Textarea
        id={inputId}
        placeholder={param.placeholder || t('templates:wizard.placeholder.string', { name })}
        value={(value as string) || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={4}
        className={cn(error && 'border-destructive')}
      />
    );
  }

  // Number type - number input
  if (param.type === 'int' || param.type === 'float') {
    return (
      <Input
        id={inputId}
        type="number"
        placeholder={param.placeholder || t('templates:wizard.placeholder.number')}
        value={value !== undefined && value !== null ? String(value) : ''}
        onChange={(e) => {
          const text = e.target.value;
          if (text === '') {
            onChange(undefined);
          } else {
            const num = param.type === 'int' ? parseInt(text, 10) : parseFloat(text);
            onChange(isNaN(num) ? text : num);
          }
        }}
        disabled={disabled}
        min={param.validation?.min}
        max={param.validation?.max}
        step={param.type === 'int' ? 1 : 'any'}
        className={cn(error && 'border-destructive')}
      />
    );
  }

  // Default: string input
  return (
    <Input
      id={inputId}
      type="text"
      placeholder={param.placeholder || t('templates:wizard.placeholder.string', { name })}
      value={(value as string) || ''}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={cn(error && 'border-destructive')}
    />
  );
}

export function TemplateWizard({
  template,
  onSubmit,
  onCancel,
  disabled = false,
  initialValues = {},
}: TemplateWizardProps) {
  const { t } = useTranslation(['templates', 'common']);
  const [parameters, setParameters] = useState<Record<string, unknown>>(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  // Initialize default values
  useEffect(() => {
    const defaults: Record<string, unknown> = {};
    Object.entries(template.parameters).forEach(([name, param]) => {
      if (param.default !== undefined && initialValues[name] === undefined) {
        defaults[name] = param.default;
      }
    });
    if (Object.keys(defaults).length > 0) {
      setParameters((prev) => ({ ...defaults, ...prev }));
    }
  }, [template, initialValues]);

  // Handle parameter change
  const handleParameterChange = (name: string, value: unknown) => {
    setParameters((prev) => ({ ...prev, [name]: value }));
    setTouched((prev) => ({ ...prev, [name]: true }));

    // Validate on change
    const param = template.parameters[name];
    const error = validateParameter(value, param, t);
    setErrors((prev) => {
      const next = { ...prev };
      if (error) {
        next[name] = error;
      } else {
        delete next[name];
      }
      return next;
    });
  };

  // Apply example
  const handleApplyExample = (example: TemplateExample) => {
    setParameters(example.parameters);
    setTouched({});
    setErrors({});
  };

  // Validate all parameters
  const validateAll = (): boolean => {
    const newErrors: Record<string, string> = {};
    const newTouched: Record<string, boolean> = {};

    Object.entries(template.parameters).forEach(([name, param]) => {
      newTouched[name] = true;
      const error = validateParameter(parameters[name], param, t);
      if (error) {
        newErrors[name] = error;
      }
    });

    setErrors(newErrors);
    setTouched(newTouched);
    return Object.keys(newErrors).length === 0;
  };

  // Handle submit
  const handleSubmit = () => {
    if (validateAll()) {
      onSubmit(parameters);
    }
  };

  const parameterEntries = Object.entries(template.parameters);
  const hasParameters = parameterEntries.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-start gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg border border-border bg-primary/10">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold text-foreground mb-1">
              {template.name}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t('templates:wizard.description')}
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Examples */}
          {template.examples && template.examples.length > 0 && (
            <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Lightbulb className="h-4 w-4 text-amber-500" />
                {t('templates:wizard.examples.title')}
              </div>
              <div className="space-y-2">
                {template.examples.map((example, index) => (
                  <div
                    key={index}
                    className="flex items-start justify-between gap-3 p-3 rounded-md bg-card border border-border hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-foreground mb-1">
                        {example.name}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {example.description}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleApplyExample(example)}
                      disabled={disabled}
                      className="shrink-0"
                    >
                      {t('templates:wizard.examples.use')}
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No parameters message */}
          {!hasParameters && (
            <div className="text-center py-8">
              <FileText className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">
                {t('templates:wizard.noParameters')}
              </p>
            </div>
          )}

          {/* Parameter fields */}
          {hasParameters && (
            <div className="space-y-4">
              {parameterEntries.map(([name, param]) => {
                const error = touched[name] ? errors[name] : null;
                const inputId = `param-${name}`;

                // Boolean parameters have different layout
                if (param.type === 'bool') {
                  return (
                    <div
                      key={name}
                      className="flex items-start gap-3 p-4 rounded-lg border border-border bg-card"
                    >
                      <ParameterInput
                        name={name}
                        param={param}
                        value={parameters[name]}
                        onChange={(value) => handleParameterChange(name, value)}
                        error={error}
                        disabled={disabled}
                        t={t}
                      />
                      <div className="flex-1">
                        {param.required && (
                          <Badge variant="secondary" className="ml-2 text-xs">
                            {t('templates:wizard.parameter.required')}
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={name} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor={inputId} className="text-sm font-medium text-foreground">
                        {name}
                      </Label>
                      {param.required ? (
                        <Badge variant="secondary" className="text-xs">
                          {t('templates:wizard.parameter.required')}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          ({t('common:labels.optional')})
                        </span>
                      )}
                    </div>

                    {/* Description */}
                    {param.description && (
                      <p className="text-xs text-muted-foreground">
                        {param.description}
                      </p>
                    )}

                    {/* Input field */}
                    <ParameterInput
                      name={name}
                      param={param}
                      value={parameters[name]}
                      onChange={(value) => handleParameterChange(name, value)}
                      error={error}
                      disabled={disabled}
                      t={t}
                    />

                    {/* Error message */}
                    {error && (
                      <div className="flex items-center gap-2 text-xs text-destructive">
                        <AlertCircle className="h-3 w-3" />
                        {error}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer actions */}
      <div className="p-4 border-t border-border/50 flex items-center justify-between gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={disabled}
        >
          {t('templates:wizard.actions.cancel')}
        </Button>

        <Button
          type="button"
          onClick={handleSubmit}
          disabled={disabled}
          className="gap-2"
        >
          {t('templates:wizard.actions.preview')}
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
