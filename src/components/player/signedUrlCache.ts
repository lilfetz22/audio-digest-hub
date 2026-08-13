import { supabase } from '@/integrations/supabase/client';

const TTL_SECONDS = 3600;
/** Re-sign this far before expiry so a long part never runs past its signature. */
const REFRESH_MARGIN_MS = 5 * 60 * 1000;

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
