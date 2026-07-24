import { CHART_TONE_VARS, barPercent, type ChartTone } from './charts';
import './BarList.css';

export interface BarListItem {
  label: string;
  value: number;
  /** Pre-formatted value shown at the row end; defaults to the raw value. */
  valueLabel?: string;
  tone?: ChartTone;
}

export interface BarListProps {
  items: readonly BarListItem[];
  /** Bar scale maximum; defaults to the largest item value (min 1). */
  max?: number;
  /** Accessible name for the whole list (rendered on the <ul>). */
  ariaLabel?: string;
  className?: string;
}

/**
 * Horizontal distribution bars — one labeled row per category with a
 * proportional bar and a trailing value, mirroring the `.lazyweb` histogram
 * rows. Ideal for `Record<string, number>` breakdowns (PR sizes, per-model
 * usage, error patterns). The bar is decorative; the label and value are real
 * text, so no extra ARIA is needed on each row.
 */
export function BarList({
  items,
  max,
  ariaLabel,
  className,
}: Readonly<BarListProps>) {
  const scale = Math.max(
    1,
    max ?? items.reduce((peak, item) => Math.max(peak, item.value), 0),
  );

  return (
    <ul
      className={`ac-barlist${className != null ? ` ${className}` : ''}`}
      aria-label={ariaLabel}
    >
      {items.map((item) => {
        const pct = barPercent(item.value, scale);
        return (
          <li key={item.label} className="ac-barlist__row">
            <span className="ac-barlist__label">{item.label}</span>
            <span className="ac-barlist__track" aria-hidden="true">
              <span
                className="ac-barlist__bar"
                style={{
                  width: `${pct}%`,
                  background: CHART_TONE_VARS[item.tone ?? 'info'],
                }}
              />
            </span>
            <span className="ac-barlist__value">
              {item.valueLabel ?? String(item.value)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
