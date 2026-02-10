import i18n from '@shared/i18n';

export function formatDate(timestamp: string): string {
  if (!timestamp) return '';

  try {
    const date = new Date(timestamp);

    // Handle invalid dates
    if (Number.isNaN(date.getTime())) return timestamp;

    // Use current i18n language for locale-aware formatting
    const options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    };

    return date.toLocaleString(i18n.language, options);
  } catch {
    // Return original string on any error
    return timestamp;
  }
}
