import type { ReactNode } from 'react';
import './StatTile.css';

export type StatTileTone = 'good' | 'warn' | 'bad';

export interface StatTileProps {
  /** The primary figure (pre-formatted, e.g. "112k", "87%"). */
  value: string;
  /** Short label under the value. */
  label: string;
  /** Optional secondary sub-line. */
  sub?: string;
  /** Colors the value; default is the neutral ink color. */
  tone?: StatTileTone;
  /** Optional trend visual (typically a <Sparkline>) rendered below. */
  sparkline?: ReactNode;
  className?: string;
}

/**
 * A single dashboard summary tile: big value + label + optional sub-line and
 * an optional trend visual. Mirrors the `.lazyweb` analytics stat tile.
 * Presentational — the composing screen supplies formatted strings.
 */
export function StatTile({
  value,
  label,
  sub,
  tone,
  sparkline,
  className,
}: Readonly<StatTileProps>) {
  return (
    <div className={`ac-stat-tile${className != null ? ` ${className}` : ''}`}>
      <strong
        className={
          tone != null ? `ac-stat-tile__value--${tone}` : 'ac-stat-tile__value'
        }
      >
        {value}
      </strong>
      <span className="ac-stat-tile__label">{label}</span>
      {sub != null && <span className="ac-stat-tile__sub">{sub}</span>}
      {sparkline != null && (
        <div className="ac-stat-tile__spark">{sparkline}</div>
      )}
    </div>
  );
}
