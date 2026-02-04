/**
 * Content Security Policy (CSP) Configuration for Auto Claude Electron App
 *
 * This module defines the Content Security Policy directives enforced via
 * Electron's session API (session.defaultSession.webRequest). CSP is a critical
 * defense-in-depth mechanism that restricts content sources, preventing XSS
 * attacks and code injection even if input validation is bypassed.
 *
 * ============================================================================
 * WHY CSP IS CRITICAL FOR ELECTRON APPS
 * ============================================================================
 *
 * Electron apps run with elevated privileges compared to web browsers:
 * - Access to Node.js APIs (filesystem, child processes, native modules)
 * - Access to system resources and OS-level operations
 * - Ability to execute arbitrary code on the user's machine
 * - Handle sensitive data (OAuth tokens, API keys, user credentials)
 *
 * Without CSP, a successful XSS attack could lead to:
 * - Arbitrary code execution on the user's system
 * - Exfiltration of OAuth tokens or API keys
 * - Modification of local files or project code
 * - Installation of malware or backdoors
 * - Privilege escalation via Node.js APIs
 *
 * CSP provides defense-in-depth by:
 * 1. Restricting script sources (prevents inline script injection)
 * 2. Blocking connections to untrusted origins (prevents data exfiltration)
 * 3. Limiting resource loading to whitelisted domains
 * 4. Preventing code evaluation via eval() or Function() constructor
 * 5. Protecting against clickjacking via frame-ancestors directive
 *
 * ============================================================================
 * ENFORCEMENT STRATEGY
 * ============================================================================
 *
 * This app uses a dual-layer CSP enforcement strategy:
 *
 * 1. PRIMARY: Electron session.defaultSession.webRequest API
 *    - Enforced at the network layer (see apps/frontend/src/main/index.ts)
 *    - Injects CSP headers for ALL responses
 *    - Cannot be bypassed by renderer process
 *
 * 2. FALLBACK: HTML <meta> tag (see apps/frontend/src/renderer/index.html)
 *    - Defense-in-depth if session API fails
 *    - Browser-level enforcement
 *    - Must match session API configuration exactly
 *
 * ============================================================================
 * TESTING CSP CHANGES
 * ============================================================================
 *
 * When modifying this configuration, follow these steps:
 *
 * 1. Run unit tests to verify CSP structure:
 *    npm test -- csp-enforcement.test.ts
 *
 * 2. Start the app in development mode:
 *    npm run dev
 *
 * 3. Open DevTools (Cmd/Ctrl+Option+I) and check the Console tab:
 *    - Look for CSP violation errors (should be NONE)
 *    - Violations appear as: "Refused to load... because it violates CSP"
 *    - Note which directive is being violated (script-src, img-src, etc.)
 *
 * 4. Test all app features that use external resources:
 *    - Google Fonts rendering (Inter, JetBrains Mono)
 *    - GitHub avatars/images (if Linear/GitHub integration used)
 *    - Sentry error reporting (check network tab for sentry.io requests)
 *    - Supabase storage (if user-generated content is loaded)
 *
 * 5. If legitimate violations occur:
 *    a. Identify the exact domain/source being blocked
 *    b. Verify it's necessary for app functionality
 *    c. Add to the appropriate directive with documentation
 *    d. Re-test to ensure no new violations
 *
 * ============================================================================
 * COMMON PITFALLS AND HOW TO AVOID THEM
 * ============================================================================
 *
 * ❌ WRONG: Adding 'unsafe-inline' to script-src
 *    This defeats the entire purpose of CSP. Inline scripts are the primary
 *    XSS attack vector. If you need dynamic scripts, use nonce-based CSP.
 *
 * ❌ WRONG: Adding 'unsafe-eval' to script-src
 *    Allows eval(), Function(), setTimeout(string), which enables code injection.
 *    Refactor code to avoid eval() instead of relaxing CSP.
 *
 * ❌ WRONG: Using overly broad wildcards like https://*
 *    This allows any HTTPS domain, defeating CSP's protection. Use specific
 *    domains or subdomain wildcards (https://*.example.com) instead.
 *
 * ❌ WRONG: Adding data: to script-src or connect-src
 *    data: URIs can contain executable code. Only allow data: for img-src and
 *    font-src where it's needed for base64-encoded resources.
 *
 * ✅ CORRECT: Use specific domains
 *    Instead of https://*.com, use https://fonts.googleapis.com
 *
 * ✅ CORRECT: Document every allowed source
 *    Explain WHY each domain is needed so future maintainers understand
 *
 * ✅ CORRECT: Start strict, relax only if necessary
 *    Begin with the most restrictive policy, then add exceptions based on
 *    actual CSP violations during testing
 *
 * ============================================================================
 * MODIFICATION EXAMPLES
 * ============================================================================
 *
 * Example 1: Allow WebSocket connections to a specific API
 * const CONNECT_SRC = "'self' https://*.ingest.us.sentry.io wss://api.example.com";
 * // Rationale: Required for real-time updates via WebSocket API
 *
 * Example 2: Allow images from a new CDN
 * const IMG_SRC = "'self' data: blob: https://*.githubusercontent.com https://*.supabase.co https://cdn.example.com";
 * // Rationale: CDN hosts user avatars and app assets
 *
 * Example 3: Allow external CSS framework (NOT RECOMMENDED)
 * const STYLE_SRC = "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.example.com";
 * // Rationale: Third-party UI framework requires external stylesheets
 * // WARNING: Verify the CDN is trustworthy and uses HTTPS
 *
 * ============================================================================
 *
 * IMPORTANT: Changes to this configuration should be carefully reviewed to ensure:
 * 1. All legitimate app resources remain accessible
 * 2. No overly permissive directives are introduced
 * 3. External resources are limited to trusted, necessary sources
 * 4. The policy remains as strict as possible while maintaining functionality
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
 * @see https://www.electronjs.org/docs/latest/tutorial/security#csp-http-header
 * @see https://content-security-policy.com/ - CSP reference and testing tools
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
 * This is the complete CSP that will be injected via the Electron session API
 * (see apps/frontend/src/main/index.ts). Each directive is separated by semicolons
 * (;) as per CSP specification.
 *
 * STRUCTURE:
 * - Each directive controls a specific resource type (scripts, styles, images, etc.)
 * - Directives are space-separated lists of allowed sources
 * - Sources can be keywords ('self', 'none'), URLs, or wildcards
 * - Order doesn't matter, but consistency aids readability
 *
 * MODIFICATION GUIDE - STEP BY STEP:
 *
 * STEP 1: Identify which directive to modify
 * - script-src: For JavaScript files (.js, .mjs)
 * - style-src: For stylesheets (.css, <style> tags)
 * - img-src: For images (<img>, background-image, etc.)
 * - connect-src: For fetch(), XHR, WebSocket, EventSource
 * - font-src: For web fonts (@font-face)
 * - default-src: Fallback for unspecified directives
 *
 * STEP 2: Update the directive constant above
 * - Add the new source to the appropriate directive constant
 * - Use single quotes for CSP keywords ('self', 'none', 'unsafe-inline')
 * - Use full URLs with protocol for external domains (https://example.com)
 * - Use wildcard subdomains sparingly (https://*.example.com)
 *
 * STEP 3: Document the change
 * - Add a comment explaining WHY the source is needed
 * - Include context about which feature requires it
 * - Note any security implications or trade-offs
 *
 * STEP 4: Test thoroughly
 * - Run: npm test -- csp-enforcement.test.ts
 * - Run: npm run dev
 * - Check DevTools console for CSP violations
 * - Test the feature that required the new source
 * - Verify no other features broke
 *
 * STEP 5: Review security implications
 * - Is the domain trustworthy? (HTTPS only, reputable provider)
 * - Could a narrower scope work? (specific subdomain vs wildcard)
 * - Is there a more secure alternative? (bundle locally instead of CDN)
 * - Does this enable any new attack vectors?
 *
 * DEBUGGING CSP VIOLATIONS:
 *
 * When you see a CSP violation in the console, it will look like:
 * "Refused to load the script 'https://evil.com/malware.js' because it violates
 *  the following Content Security Policy directive: 'script-src 'self''"
 *
 * To fix:
 * 1. Determine if the resource is legitimate (part of your app) or malicious
 * 2. If legitimate, identify which directive is blocking it (script-src above)
 * 3. Add the domain to that directive's constant
 * 4. If malicious, investigate how it was injected (potential XSS vulnerability)
 *
 * SECURITY CHECKLIST BEFORE RELAXING CSP:
 * [ ] Is this resource absolutely necessary for core functionality?
 * [ ] Have I verified the domain is trustworthy (check ownership, HTTPS)?
 * [ ] Could I bundle this resource locally instead of loading externally?
 * [ ] Am I using the most specific URL possible (not a broad wildcard)?
 * [ ] Have I documented WHY this exception is needed?
 * [ ] Have I tested that the app still works correctly?
 *
 * @example
 * // EXAMPLE 1: Allow WebSocket connections to a specific API
 * const CONNECT_SRC = "'self' https://*.ingest.us.sentry.io wss://api.example.com";
 * // Rationale: Real-time sync feature requires WebSocket connection to api.example.com
 *
 * @example
 * // EXAMPLE 2: Allow a new image CDN
 * const IMG_SRC = "'self' data: blob: https://*.githubusercontent.com https://*.supabase.co https://images.example.com";
 * // Rationale: User profile images are hosted on images.example.com CDN
 *
 * @example
 * // EXAMPLE 3: Allow analytics script (consider carefully!)
 * const SCRIPT_SRC = "'self' https://cdn.analytics.com";
 * // Rationale: Third-party analytics for usage tracking
 * // WARNING: This allows third-party JS execution - verify the provider is trustworthy
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
 * This is a runtime validation helper for testing CSP enforcement. It ensures
 * that the CSP policy includes all critical directives to prevent accidental
 * omissions that could leave security gaps.
 *
 * USAGE:
 * - Called in unit tests to verify CSP_CONFIG structure
 * - Can be used at runtime to validate CSP headers
 * - Useful for CI/CD pipelines to catch CSP regressions
 *
 * LIMITATIONS:
 * - Only checks that directive names are present, not their values
 * - Does not validate the strictness of each directive
 * - Does not detect overly permissive sources like 'unsafe-inline' in script-src
 *
 * For comprehensive CSP validation, also:
 * 1. Review each directive's allowed sources manually
 * 2. Test in browser to ensure no legitimate violations
 * 3. Use CSP analysis tools like https://csp-evaluator.withgoogle.com/
 *
 * @param cspString - The CSP string to validate (e.g., "default-src 'self'; script-src 'self'")
 * @returns true if all required directives are present, false otherwise
 *
 * @example
 * const isValid = validateCSP(CSP_CONFIG);
 * if (!isValid) {
 *   console.error('CSP is missing required directives!');
 * }
 */
export function validateCSP(cspString: string): boolean {
  const requiredDirectives = Object.keys(CSP_DIRECTIVES);
  return requiredDirectives.every(directive => cspString.includes(directive));
}

/**
 * ============================================================================
 * CSP RELATIONSHIP WITH OTHER SECURITY FEATURES
 * ============================================================================
 *
 * CSP is ONE LAYER in a defense-in-depth security strategy. It works alongside:
 *
 * 1. CONTEXT ISOLATION (apps/frontend/src/main/index.ts)
 *    - Separates renderer process from Node.js APIs
 *    - Prevents direct access to require() or Electron APIs
 *    - CSP complements this by preventing script injection in the renderer
 *
 * 2. NODE INTEGRATION DISABLED (apps/frontend/src/main/index.ts)
 *    - Disables Node.js in renderer process
 *    - Prevents access to fs, child_process, etc.
 *    - CSP prevents loading external scripts that could try to re-enable it
 *
 * 3. SANDBOX MODE (apps/frontend/src/main/index.ts)
 *    - Runs renderer in Chromium sandbox (OS-level isolation)
 *    - Limits impact of renderer compromise
 *    - CSP adds additional content restrictions on top of sandbox
 *
 * 4. INPUT VALIDATION (throughout the app)
 *    - Sanitizes user input to prevent XSS
 *    - First line of defense against injection attacks
 *    - CSP acts as a safety net if validation is bypassed
 *
 * 5. PRELOAD SCRIPT ISOLATION (apps/frontend/src/preload.ts)
 *    - Exposes only necessary APIs to renderer
 *    - Prevents renderer from accessing full Electron API
 *    - CSP prevents malicious scripts from calling exposed APIs
 *
 * DEFENSE IN DEPTH PRINCIPLE:
 * Even if one layer fails (e.g., XSS bypasses input validation), CSP prevents
 * the attacker from loading external malicious scripts or exfiltrating data to
 * untrusted domains. Multiple layers failing simultaneously is far less likely
 * than a single layer failing.
 *
 * ============================================================================
 */
