# Spec Summary Card

The `SpecSummaryCard` component provides a visual overview of spec statistics in the Productivity Dashboard.

## Location

`apps/frontend/src/renderer/components/analytics/SpecSummaryCard.tsx`

## What It Shows

The card displays four key metrics:

| Metric | Description | Variant Logic |
|--------|-------------|---------------|
| **Total Specs** | Count of all tracked specs | Always default |
| **Completed** | Completed specs with completion rate percentage | Green (>=80%), Yellow (>=50%), Default (<50%) |
| **In Progress** | Currently active specs | Yellow if >0, Default if 0 |
| **Avg QA Iterations** | Average QA review cycles per spec | Green (<=1), Yellow (<=2), Red (>2) |

Below the stat tiles, a **Workflow Type Breakdown** section shows spec counts grouped by workflow type (e.g., simple, standard, complex), sorted by frequency.

## States

- **Loading** -- Shows a spinner with loading text
- **Empty** -- Shown when no specs exist yet; includes a hint message
- **Data** -- Renders stat tiles and workflow breakdown

## Integration

The card is rendered inside `ProductivityDashboard.tsx`, immediately after `MetricsSummaryCard`:

```tsx
<SpecSummaryCard analytics={summary} isLoading={isLoading} />
```

## Internationalization

All user-facing text uses i18n keys from the `analytics` namespace under `specSummary.*`. Translations are provided in both English and French:

- `apps/frontend/src/shared/i18n/locales/en/analytics.json`
- `apps/frontend/src/shared/i18n/locales/fr/analytics.json`

## Props

```typescript
interface SpecSummaryCardProps {
  readonly analytics: ProductivitySummary | null;
  readonly isLoading?: boolean;  // default: false
}
```

The component derives all displayed values from the `ProductivitySummary` type via `useMemo`.
