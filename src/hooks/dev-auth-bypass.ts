import type { User } from '@supabase/supabase-js';

/**
 * Opt-in, dev-only login bypass for exercising ProtectedRoute-gated pages
 * (Dashboard/Settings/Player/etc.) without a real Supabase session.
 *
 * Visit any URL with `?devauth=1` to turn it on for the tab (persisted in
 * sessionStorage so it survives the redirect off `/`); `?devauth=0` turns it
 * back off. Normal `npm run dev` usage is unaffected until you opt in.
 *
 * The injected user is synthetic — Dashboard/Settings still call the real
 * Supabase backend, but with no real JWT, so RLS returns empty results
 * rather than real data. That's enough to verify rendering and effect/fetch
 * behavior (e.g. no infinite re-fetch loops) without needing test credentials.
 *
 * `import.meta.env.DEV` is statically false in production builds, so this
 * module's checks are dead-code-eliminated — see the existing `/devtest`
 * route in App.tsx for the same pattern.
 */

const STORAGE_KEY = 'audio-digest-hub:dev-auth-bypass';

export const DEV_MOCK_USER: User = {
  id: '00000000-0000-4000-8000-000000000000',
  aud: 'authenticated',
  app_metadata: {},
  user_metadata: {},
  email: 'dev-bypass@localhost',
  created_at: '1970-01-01T00:00:00.000Z',
};

/** Reads `?devauth=` off the current URL and persists the resulting on/off state. */
function syncDevAuthBypassFromUrl(): void {
  const params = new URLSearchParams(window.location.search);
  if (!params.has('devauth')) return;

  if (params.get('devauth') === '0') {
    sessionStorage.removeItem(STORAGE_KEY);
  } else {
    sessionStorage.setItem(STORAGE_KEY, '1');
  }
}

/** Call once on app/provider mount. Returns whether the bypass is active. */
export function resolveDevAuthBypass(): boolean {
  if (!import.meta.env.DEV) return false;
  syncDevAuthBypassFromUrl();
  return sessionStorage.getItem(STORAGE_KEY) === '1';
}

export function clearDevAuthBypass(): void {
  if (!import.meta.env.DEV) return;
  sessionStorage.removeItem(STORAGE_KEY);
}

export function isDevAuthBypassEnabled(): boolean {
  return import.meta.env.DEV && sessionStorage.getItem(STORAGE_KEY) === '1';
}
