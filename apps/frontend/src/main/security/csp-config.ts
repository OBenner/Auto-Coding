/**
 * Content Security Policy (CSP) Configuration for Auto Claude Electron App
 *
 * This module defines the Content Security Policy directives enforced via
 * Electron's session API (session.defaultSession.webRequest). CSP is a critical
 * defense-in-depth mechanism that restricts content sources, preventing XSS
 * attacks and code injection even if input validation is bypassed.
 *
 * IMPORTANT: Changes to this configuration should be carefully reviewed to ensure:
 * 1. All legitimate app resources remain accessible
 * 2. No overly permissive directives are introduced
 * 3. External resources are limited to trusted, necessary sources
 * 4. The policy remains as strict as possible while maintaining functionality
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
 * @see https://www.electronjs.org/docs/latest/tutorial/security#csp-http-header
 */

/**
 * Default source directive - defines the default policy for fetching resources.
 *
 * Allowed sources:
 * - 'self': Application's own origin (file:// protocol in Electron)
 * - https://fonts.googleapis.com: Google Fonts CSS files (Inter, JetBrains Mono)
 * - https://fonts.gstatic.com: Google Fonts font files (WOFF2, etc.)
 *
 * SECURITY NOTE: 'self' in Electron refers to the file:// protocol origin.
 * Additional protocols must be explicitly allowed in specific directives.
 */
const DEFAULT_SRC = "'self' https://fonts.googleapis.com https://fonts.gstatic.com";

/**
 * Script source directive - controls which scripts can be executed.
 *
 * Allowed sources:
 * - 'self': Only scripts from the application bundle
 *
 * SECURITY NOTE: No 'unsafe-inline' or 'unsafe-eval' allowed. All scripts must
 * come from the application bundle. This prevents injection of malicious scripts
 * even if an XSS vulnerability exists elsewhere.
 */
const SCRIPT_SRC = "'self'";

/**
 * Style source directive - controls which stylesheets can be loaded.
 *
 * Allowed sources:
 * - 'self': Application's own stylesheets
 * - 'unsafe-inline': Inline styles (required for React styled-components, Tailwind)
 * - https://fonts.googleapis.com: Google Fonts CSS
 *
 * SECURITY NOTE: 'unsafe-inline' is required for CSS-in-JS solutions used in the
 * React frontend. While less secure than strict CSP, it's necessary for the UI
 * framework. Consider migrating to nonce-based CSP in the future if feasible.
 */
const STYLE_SRC = "'self' 'unsafe-inline' https://fonts.googleapis.com";

/**
 * Image source directive - controls which images can be loaded.
 *
 * Allowed sources:
 * - 'self': Application's own images
 * - data: Data URIs (base64-encoded images, common in React)
 * - blob: Blob URLs (dynamically generated images, canvas exports)
 * - https://*.githubusercontent.com: GitHub user avatars, issue images
 * - https://*.supabase.co: Supabase storage (if used for user-generated content)
 *
 * SECURITY NOTE: Wildcards (*.domain) are less secure than specific subdomains
 * but necessary for CDNs with dynamic subdomains. GitHub and Supabase use
 * content-addressed storage which mitigates some risks.
 */
const IMG_SRC = "'self' data: blob: https://*.githubusercontent.com https://*.supabase.co";

/**
 * Connect source directive - controls which URLs can be loaded via fetch/XHR/WebSocket.
 *
 * Allowed sources:
 * - 'self': API calls to backend (if local server is used)
 * - https://*.ingest.us.sentry.io: Sentry error reporting and performance monitoring
 *
 * SECURITY NOTE: This is the most critical directive for data exfiltration prevention.
 * Only add domains here if absolutely necessary for app functionality. Sentry is
 * required for error tracking and uses a wildcard for regional endpoints.
 */
const CONNECT_SRC = "'self' https://*.ingest.us.sentry.io";

/**
 * Font source directive - controls which fonts can be loaded.
 *
 * Allowed sources:
 * - 'self': Local font files bundled with the app
 * - https://fonts.gstatic.com: Google Fonts CDN (serves .woff2 files)
 * - data: Data URI fonts (inline base64-encoded fonts)
 *
 * SECURITY NOTE: Font files can contain executable code in some edge cases.
 * Limiting to trusted CDNs and bundled fonts reduces this risk.
 */
const FONT_SRC = "'self' https://fonts.gstatic.com data:";

/**
 * Object source directive - controls <object>, <embed>, and <applet> elements.
 *
 * Value:
 * - 'none': No plugins or embedded objects allowed
 *
 * SECURITY NOTE: Plugins like Flash are a major attack vector. Electron apps
 * should never need embedded objects. Keep this as 'none' unless absolutely
 * necessary.
 */
const OBJECT_SRC = "'none'";

/**
 * Base URI directive - restricts the URLs that can be used in <base> element.
 *
 * Value:
 * - 'self': Only the application's own origin
 *
 * SECURITY NOTE: Prevents attackers from changing the base URL to redirect
 * relative URLs to malicious sites.
 */
const BASE_URI = "'self'";

/**
 * Form action directive - controls where forms can submit data.
 *
 * Value:
 * - 'self': Forms can only submit to the application's own origin
 *
 * SECURITY NOTE: Prevents forms from being hijacked to submit data to
 * attacker-controlled servers.
 */
const FORM_ACTION = "'self'";

/**
 * Frame ancestors directive - controls which origins can embed this app in frames.
 *
 * Value:
 * - 'none': The application cannot be embedded in any frame/iframe
 *
 * SECURITY NOTE: Electron apps should never be embedded in frames. This prevents
 * clickjacking attacks. Use 'none' to completely disallow framing.
 */
const FRAME_ANCESTORS = "'none'";

/**
 * Full Content Security Policy string.
 *
 * This is the complete CSP that will be injected via the Electron session API.
 * Each directive is separated by semicolons (;) as per CSP specification.
 *
 * MODIFICATION GUIDE:
 * 1. To add a new allowed source, update the relevant directive constant above
 * 2. Document WHY the source is needed (e.g., "Required for OAuth flow")
 * 3. Use specific domains instead of wildcards when possible
 * 4. Test in development to ensure no console CSP violation errors
 * 5. If violations occur, determine if they're legitimate before relaxing CSP
 *
 * @example
 * // To allow WebSocket connections to a specific domain:
 * const CONNECT_SRC = "'self' https://*.ingest.us.sentry.io wss://api.example.com";
 */
export const CSP_CONFIG = [
  `default-src ${DEFAULT_SRC}`,
  `script-src ${SCRIPT_SRC}`,
  `style-src ${STYLE_SRC}`,
  `img-src ${IMG_SRC}`,
  `connect-src ${CONNECT_SRC}`,
  `font-src ${FONT_SRC}`,
  `object-src ${OBJECT_SRC}`,
  `base-uri ${BASE_URI}`,
  `form-action ${FORM_ACTION}`,
  `frame-ancestors ${FRAME_ANCESTORS}`
].join('; ');

/**
 * Type-safe CSP configuration for use in tests and validation.
 *
 * This object provides a structured way to access individual directives
 * for testing and debugging purposes.
 */
export const CSP_DIRECTIVES = {
  'default-src': DEFAULT_SRC,
  'script-src': SCRIPT_SRC,
  'style-src': STYLE_SRC,
  'img-src': IMG_SRC,
  'connect-src': CONNECT_SRC,
  'font-src': FONT_SRC,
  'object-src': OBJECT_SRC,
  'base-uri': BASE_URI,
  'form-action': FORM_ACTION,
  'frame-ancestors': FRAME_ANCESTORS
} as const;

/**
 * Validate that a CSP string contains all required directives.
 *
 * This is a runtime validation helper for testing CSP enforcement.
 *
 * @param cspString - The CSP string to validate
 * @returns true if all required directives are present
 */
export function validateCSP(cspString: string): boolean {
  const requiredDirectives = Object.keys(CSP_DIRECTIVES);
  return requiredDirectives.every(directive => cspString.includes(directive));
}
