/**
 * Dev-only harness for the multi-part transition, with two selectable modes so a
 * real device can A/B the bug against the fix:
 *
 *   /devtest?mode=legacy  reproduces the pre-fix structure: the <audio> element is
 *                         unmounted on part change and .play() is called on the
 *                         freshly mounted replacement from its canplay handler.
 *   /devtest?mode=fixed   the shipped code path: one persistent element whose src
 *                         is swapped synchronously inside the `ended` handler.
 *
 * All diagnostics are rendered on screen, large: iOS Safari cannot be remote
 * inspected from Windows, so the phone itself has to report what happened.
 *
 * The audio fixtures are gitignored. Generate them once with:
 *   node scripts/gen-devtest-audio.mjs
 *
 * Not routed in production builds.
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useAudioPlayer } from '@/components/player/useAudioPlayer';

interface Audiobook {
  id: string;
  title: string;
  duration_seconds: number;
  last_playback_position_seconds: number;
  storage_path: string;
  chapters_json: Record<string, number> | null;
}

const PARTS: Audiobook[] = [1, 2, 3].map((p) => ({
  id: `part-${p}`,
  title: `Dev Digest (Part ${p} of 3)`,
  duration_seconds: 120,
  last_playback_position_seconds: 0,
  storage_path: `/devtest-part${p}.wav`,
  chapters_json: null,
}));

/** Stand-in for the network latency of `select` + `createSignedUrl`. */
const FETCH_DELAY_MS = 250;
/** Leaves ~15s of real time at 2x — enough to lock the phone after tapping. */
const SEEK_MARGIN_SECONDS = 30;

const nextOf = (id: string) => PARTS[Number(id.split('-')[1])] ?? null;

type LogFn = (msg: string) => void;

const useEventLog = () => {
  const [lines, setLines] = useState<string[]>([]);
  const log = useCallback<LogFn>((msg) => {
    const stamp = new Date().toTimeString().slice(0, 8);
    console.log(`[devtest] ${msg}`);
    setLines((prev) => [`${stamp}  ${msg}`, ...prev].slice(0, 40));
  }, []);
  return { lines, log };
};

/** Big, high-contrast readout — this is the only debugger available on iOS/Windows. */
const Diagnostics = ({
  mode,
  part,
  elements,
  autoPlayError,
  audio,
  lines,
}: {
  mode: string;
  part: string;
  elements: number;
  autoPlayError: string | null;
  audio: HTMLAudioElement | null;
  lines: string[];
}) => {
  const [, force] = useState(0);
  useEffect(() => {
    const t = setInterval(() => force((n) => n + 1), 400);
    return () => clearInterval(t);
  }, []);

  const row = (k: string, v: string, warn = false) => (
    <div className="flex justify-between border-b border-gray-200 py-1">
      <span className="text-gray-500">{k}</span>
      <span className={warn ? 'font-bold text-red-600' : 'font-bold'}>{v}</span>
    </div>
  );

  return (
    <div className="space-y-3 text-base">
      {autoPlayError && (
        <div className="rounded bg-red-600 p-3 text-white">
          <div className="text-sm uppercase tracking-wide">Autoplay was blocked</div>
          <div className="font-mono text-lg break-all">{autoPlayError}</div>
        </div>
      )}
      <div className="rounded bg-gray-50 p-3 font-mono text-sm">
        {row('mode', mode, mode === 'legacy')}
        {row('current part', part)}
        {row('playing', audio ? String(!audio.paused) : 'n/a', !!audio && audio.paused)}
        {row('rate', audio ? `${audio.playbackRate}x` : 'n/a', !!audio && audio.playbackRate !== 2)}
        {row('time', audio ? `${audio.currentTime.toFixed(1)} / ${(audio.duration || 0).toFixed(0)}s` : 'n/a')}
        {row('file', (audio?.currentSrc ?? '').split('/').pop() || '-')}
        {row('<audio> elements created', String(elements), elements > 1)}
      </div>
      <div className="rounded bg-black p-2 font-mono text-xs text-green-400">
        {lines.length === 0 ? '(no events yet)' : lines.map((l, i) => <div key={i}>{l}</div>)}
      </div>
    </div>
  );
};

const Buttons = ({
  onPlay,
  onSeek,
  playing,
}: {
  onPlay: () => void;
  onSeek: () => void;
  playing: boolean;
}) => (
  <div className="flex flex-col gap-3">
    <button
      id="btn-play"
      className="rounded bg-blue-600 px-4 py-4 text-lg font-semibold text-white"
      onClick={onPlay}
    >
      {playing ? 'Pause' : 'Play'}
    </button>
    <button
      id="btn-near-end"
      className="rounded border-2 border-blue-600 px-4 py-4 text-lg font-semibold text-blue-700"
      onClick={onSeek}
    >
      Jump to {SEEK_MARGIN_SECONDS}s before end, then lock the phone
    </button>
  </div>
);

/* ------------------------------------------------------------------ legacy */

/** Mirrors the pre-fix Player.tsx: conditional render unmounts <audio>. */
const LegacyHarness = () => {
  const { lines, log } = useEventLog();
  const [id, setId] = useState('part-1');
  const [audiobook, setAudiobook] = useState<Audiobook | null>(null);
  const [audioUrl, setAudioUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [autoPlayError, setAutoPlayError] = useState<string | null>(null);
  const [elements, setElements] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const pendingAutoPlayRef = useRef(false);
  const seen = useRef(new Set<HTMLAudioElement>());

  useEffect(() => {
    // The pre-fix reset: blows away state, so the loading branch unmounts <audio>.
    setAudiobook(null);
    setAudioUrl('');
    setLoading(true);
    const t = setTimeout(() => {
      const book = PARTS.find((p) => p.id === id)!;
      setAudiobook(book);
      setAudioUrl(book.storage_path);
      setLoading(false);
    }, FETCH_DELAY_MS);
    return () => clearTimeout(t);
  }, [id]);

  const handleEnded = () => {
    const next = nextOf(id);
    if (!next) return log('ended — no further parts');
    log('ended → async lookup, then remount');
    setTimeout(() => {
      pendingAutoPlayRef.current = true;
      setId(next.id);
    }, FETCH_DELAY_MS);
  };

  return (
    <div className="mx-auto max-w-md space-y-4 p-4">
      <h1 className="text-xl font-bold">Legacy (pre-fix)</h1>
      {loading || !audiobook ? (
        <div>Loading…</div>
      ) : (
        <>
          <audio
            ref={(el) => {
              audioRef.current = el;
              if (el && !seen.current.has(el)) {
                seen.current.add(el);
                setElements(seen.current.size);
              }
            }}
            src={audioUrl}
            preload="metadata"
            onEnded={handleEnded}
            onPlay={() => log('play')}
            onCanPlay={() => {
              if (!pendingAutoPlayRef.current) return;
              pendingAutoPlayRef.current = false;
              log('auto-play attempt on NEW element');
              audioRef.current?.play().catch((err) => {
                setAutoPlayError(`${err.name}: ${err.message}`);
                log(`FAILED: ${err.name}`);
              });
            }}
          />
          <Buttons
            playing={!!audioRef.current && !audioRef.current.paused}
            onPlay={() => {
              setAutoPlayError(null);
              const a = audioRef.current;
              if (!a) return;
              if (a.paused) void a.play().catch((e) => setAutoPlayError(`${e.name}: ${e.message}`));
              else a.pause();
            }}
            onSeek={() => {
              const a = audioRef.current;
              if (a?.duration) a.currentTime = Math.max(0, a.duration - SEEK_MARGIN_SECONDS);
            }}
          />
        </>
      )}
      <Diagnostics
        mode="legacy"
        part={audiobook?.title ?? '-'}
        elements={elements}
        autoPlayError={autoPlayError}
        audio={audioRef.current}
        lines={lines}
      />
    </div>
  );
};

/* ------------------------------------------------------------------- fixed */

/** Mirrors the shipped Player.tsx: one persistent element, src swapped in place. */
const FixedHarness = () => {
  const { lines, log } = useEventLog();
  const [id, setId] = useState('part-1');
  const [audiobook, setAudiobook] = useState<Audiobook | null>(null);
  const [audioUrl, setAudioUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [nextPart, setNextPart] = useState<{ id: string; url: string } | null>(null);
  const [elements, setElements] = useState(0);

  const audiobookRef = useRef<Audiobook | null>(null);
  const nextPartRef = useRef<{ id: string; url: string } | null>(null);
  const pendingAutoPlayRef = useRef(false);
  const seen = useRef(new Set<HTMLAudioElement>());

  useEffect(() => {
    audiobookRef.current = audiobook;
  }, [audiobook]);
  useEffect(() => {
    nextPartRef.current = nextPart;
  }, [nextPart]);

  const goToNextPart = useCallback(
    (options: { autoPlay: boolean }) => {
      const next = nextPartRef.current;
      if (!next) return log('no further parts');
      log(`swapping src to ${next.id} in place`);
      loadSource(next.url, { autoPlay: options.autoPlay, startAt: 0 });
      pendingAutoPlayRef.current = options.autoPlay;
      setId(next.id);
    },
    // `loadSource` comes from the hook call below and cannot be listed here; it
    // is stable, and this body only runs after mount. Same shape as Player.tsx.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [log],
  );

  const handleEnded = useCallback(() => {
    log('ended → swapping synchronously');
    goToNextPart({ autoPlay: true });
  }, [goToNextPart, log]);

  const player = useAudioPlayer(audiobook, handleEnded, () => goToNextPart({ autoPlay: true }));
  const { attachAudio, loadSource } = player;

  useEffect(() => {
    let cancelled = false;
    if (!audiobookRef.current) setLoading(true);
    const t = setTimeout(() => {
      if (cancelled) return;
      const book = PARTS.find((p) => p.id === id)!;
      setAudiobook(book);
      setAudioUrl(book.storage_path);
      setLoading(false);
    }, FETCH_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [id]);

  useEffect(() => {
    if (!audioUrl || !audiobook) return;
    const shouldAutoPlay = pendingAutoPlayRef.current;
    pendingAutoPlayRef.current = false;
    loadSource(audioUrl, {
      autoPlay: shouldAutoPlay,
      startAt: audiobook.last_playback_position_seconds,
    });
  }, [audioUrl, audiobook, loadSource]);

  useEffect(() => {
    if (!audiobook) return setNextPart(null);
    const next = nextOf(audiobook.id);
    if (!next) return setNextPart(null);
    const t = setTimeout(
      () => setNextPart({ id: next.id, url: next.storage_path }),
      FETCH_DELAY_MS,
    );
    return () => clearTimeout(t);
  }, [audiobook]);

  return (
    <div className="mx-auto max-w-md space-y-4 p-4">
      {/* Persistent element — never unmounted, no src prop. */}
      <audio
        ref={(el) => {
          attachAudio(el);
          if (el && !seen.current.has(el)) {
            seen.current.add(el);
            setElements(seen.current.size);
          }
        }}
        preload="auto"
      />
      <h1 className="text-xl font-bold">Fixed</h1>
      {loading && !audiobook ? (
        <div>Loading…</div>
      ) : (
        <Buttons
          playing={player.isPlaying}
          onPlay={() => void player.togglePlayPause()}
          onSeek={() => {
            const a = player.audioRef.current;
            if (a?.duration) a.currentTime = Math.max(0, a.duration - SEEK_MARGIN_SECONDS);
          }}
        />
      )}
      <Diagnostics
        mode="fixed"
        part={audiobook?.title ?? '-'}
        elements={elements}
        autoPlayError={player.error}
        audio={player.audioRef.current}
        lines={lines}
      />
    </div>
  );
};

const DevPlayerTest = () => {
  const mode = new URLSearchParams(window.location.search).get('mode') ?? 'fixed';
  return (
    <div>
      <div className="flex gap-2 p-4 pb-0 text-sm">
        <a className="underline" href="/devtest?mode=fixed">
          fixed
        </a>
        <a className="underline" href="/devtest?mode=legacy">
          legacy
        </a>
      </div>
      {mode === 'legacy' ? <LegacyHarness /> : <FixedHarness />}
    </div>
  );
};

export default DevPlayerTest;
