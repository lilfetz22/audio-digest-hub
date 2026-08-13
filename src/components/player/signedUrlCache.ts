import { supabase } from '@/integrations/supabase/client';

/** Long enough that one path yields a byte-identical URL for a whole session. */
const TTL_SECONDS = 12 * 60 * 60;
/** Re-sign this far ahead so no part is ever started on a nearly-expired signature. */
const REFRESH_MARGIN_MS = 2 * 60 * 60 * 1000;

interface CacheEntry {
  url: string;
  expiresAt: number;
}

const cache = new Map<string, CacheEntry>();
const inflight = new Map<string, Promise<string>>();

/**
 * Signs `storagePath` for playback, returning the *same* URL string for as long
 * as the signature is valid.
 *
 * Stability is the point: the player compares the URL it is about to load
 * against the one already loaded and skips the assignment when they match. A
 * fresh signature for a file that is already playing would look like a new
 * source, and re-assigning `audio.src` restarts playback from zero.
 */
export async function getSignedAudioUrl(storagePath: string): Promise<string> {
  const cached = cache.get(storagePath);
  if (cached && cached.expiresAt - REFRESH_MARGIN_MS > Date.now()) {
    return cached.url;
  }

  const pending = inflight.get(storagePath);
  if (pending) return pending;

  const request = supabase.storage
    .from('audiobooks')
    .createSignedUrl(storagePath, TTL_SECONDS)
    .then(({ data, error }) => {
      if (error || !data?.signedUrl) {
        throw error ?? new Error(`Failed to sign audio URL for ${storagePath}`);
      }
      cache.set(storagePath, {
        url: data.signedUrl,
        expiresAt: Date.now() + TTL_SECONDS * 1000,
      });
      return data.signedUrl;
    })
    .finally(() => {
      inflight.delete(storagePath);
    });

  inflight.set(storagePath, request);
  return request;
}

/**
 * Drops every cached/in-flight signed URL. A signed URL is a per-user bearer
 * capability for the RLS-scoped `audiobooks` bucket, so it should not keep
 * working for the rest of its TTL after the user signs out on a shared device.
 */
export function clearSignedAudioUrlCache() {
  cache.clear();
  inflight.clear();
}

supabase.auth.onAuthStateChange((event) => {
  if (event === 'SIGNED_OUT' || event === 'USER_UPDATED') clearSignedAudioUrlCache();
});
