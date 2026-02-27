/**
 * TemplatePreview - Display generated spec preview from template
 *
 * Features:
 * - Renders generated spec with markdown support
 * - Shows title, description, rationale, user stories, acceptance criteria
 * - Technical details and test coverage requirements
 * - Scrollable content with clean layout
 */
import { useTranslation } from 'react-i18next';
import {
  FileText,
  Target,
  Users,
  CheckCircle2,
  Code2,
  TestTube2,
  Package,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { GeneratedSpec } from '../../../shared/types';

interface TemplatePreviewProps {
  spec: GeneratedSpec;
  className?: string;
}

/**
 * Section component for consistent spec section rendering
 */
function SpecSection({
  icon: Icon,
  title,
  children,
  className,
}: {
  icon: typeof FileText;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <Icon className="h-4 w-4 text-primary" />
        {title}
      </div>
      <div className="pl-6">{children}</div>
    </div>
  );
}

export function TemplatePreview({ spec, className }: TemplatePreviewProps) {
  const { t } = useTranslation(['templates', 'common']);

  return (
    <ScrollArea className={cn('h-full', className)}>
      <div className="p-4 space-y-6">
        {/* Title */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-bold text-foreground">{spec.title}</h2>
          </div>
          {spec.description && (
            <p className="text-sm text-muted-foreground pl-7">
              {spec.description}
            </p>
          )}
        </div>

        {/* Divider */}
        <div className="border-t border-border/50" />

        {/* Rationale */}
        {spec.rationale && (
          <SpecSection
            icon={Target}
            title={t('templates:preview.sections.rationale')}
          >
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {spec.rationale}
              </ReactMarkdown>
            </div>
          </SpecSection>
        )}

        {/* User Stories */}
        {spec.user_stories && spec.user_stories.length > 0 && (
          <SpecSection
            icon={Users}
            title={t('templates:preview.sections.userStories')}
          >
            <ul className="space-y-2">
              {spec.user_stories.map((story, index) => (
                <li
                  key={index}
                  className="flex items-start gap-2 text-sm text-foreground"
                >
                  <span className="text-primary mt-0.5">•</span>
                  <span className="flex-1">{story}</span>
                </li>
              ))}
            </ul>
          </SpecSection>
        )}

        {/* Acceptance Criteria */}
        {spec.acceptance_criteria && spec.acceptance_criteria.length > 0 && (
          <SpecSection
            icon={CheckCircle2}
            title={t('templates:preview.sections.acceptanceCriteria')}
          >
            <ul className="space-y-2">
              {spec.acceptance_criteria.map((criteria, index) => (
                <li
                  key={index}
                  className="flex items-start gap-2 rounded-lg border border-border bg-secondary/30 p-3 text-sm text-foreground"
                >
                  <CheckCircle2 className="h-4 w-4 text-success mt-0.5 shrink-0" />
                  <span className="flex-1">{criteria}</span>
                </li>
              ))}
            </ul>
          </SpecSection>
        )}

        {/* Technical Details */}
        {spec.technical_details && (
          <SpecSection
            icon={Code2}
            title={t('templates:preview.sections.technicalDetails')}
          >
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {spec.technical_details}
              </ReactMarkdown>
            </div>
          </SpecSection>
        )}

        {/* Test Coverage Requirements */}
        {spec.test_coverage && spec.test_coverage.length > 0 && (
          <SpecSection
            icon={TestTube2}
            title={t('templates:preview.sections.testCoverage')}
          >
            <ul className="space-y-2">
              {spec.test_coverage.map((test, index) => (
                <li
                  key={index}
                  className="flex items-start gap-2 text-sm text-muted-foreground"
                >
                  <TestTube2 className="h-3 w-3 text-info mt-1 shrink-0" />
                  <span className="flex-1">{test}</span>
                </li>
              ))}
            </ul>
          </SpecSection>
        )}

        {/* Dependencies */}
        {spec.dependencies && spec.dependencies.length > 0 && (
          <SpecSection
            icon={Package}
            title={t('templates:preview.sections.dependencies')}
          >
            <div className="flex flex-wrap gap-2">
              {spec.dependencies.map((dep, index) => (
                <Badge
                  key={index}
                  variant="secondary"
                  className="text-xs font-mono"
                >
                  <Package className="mr-1 h-3 w-3" />
                  {dep}
                </Badge>
              ))}
            </div>
          </SpecSection>
        )}

        {/* Empty state */}
        {!spec.rationale &&
          (!spec.user_stories || spec.user_stories.length === 0) &&
          (!spec.acceptance_criteria || spec.acceptance_criteria.length === 0) &&
          !spec.technical_details &&
          (!spec.test_coverage || spec.test_coverage.length === 0) &&
          (!spec.dependencies || spec.dependencies.length === 0) && (
            <div className="text-center py-12">
              <FileText className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground mb-1">
                {t('templates:preview.empty.title')}
              </p>
              <p className="text-xs text-muted-foreground/70">
                {t('templates:preview.empty.description')}
              </p>
            </div>
          )}
      </div>
    </ScrollArea>
  );
}
