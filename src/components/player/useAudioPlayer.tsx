import { useState, useRef, useEffect, useCallback } from 'react';
import { supabase } from '@/integrations/supabase/client';

interface Audiobook {
  id: string;
  title: string;
  duration_seconds: number;
  last_playback_position_seconds: number;
  storage_path: string;
  chapters_json: Record<string, number> | null;
}

export interface LoadSourceOptions {
  /** Start playing as soon as the source is assigned. */
  autoPlay?: boolean;
  /** Resume position in seconds, applied once metadata is available. */
  startAt?: number;
}

const RATE_STORAGE_KEY = 'audioPlayer.playbackRate';
const DEFAULT_PLAYBACK_RATE = 2;
/** A saved position this close to the end means the part was finished, not paused. */
const END_OF_PART_TOLERANCE_SECONDS = 1;

const MEDIA_SESSION_ACTIONS: MediaSessionAction[] = [
  'play',
  'pause',
  'seekbackward',
  'seekforward',
  'seekto',
  'nexttrack',
];

const readStoredPlaybackRate = (): number => {
  try {
    const parsed = parseFloat(window.localStorage.getItem(RATE_STORAGE_KEY) ?? '');
    return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_PLAYBACK_RATE;
  } catch {
    return DEFAULT_PLAYBACK_RATE;
  }
};

export const useAudioPlayer = (
  audiobook: Audiobook | null,
  onEnded?: () => void,
  onNextTrack?: () => void,
) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioEl, setAudioEl] = useState<HTMLAudioElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(readStoredPlaybackRate);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSeeking, setIsSeeking] = useState(false);

  const onEndedRef = useRef(onEnded);
  const onNextTrackRef = useRef(onNextTrack);
  const audiobookRef = useRef(audiobook);
  const rateRef = useRef(playbackRate);
  const isSeekingRef = useRef(false);
  /** URL currently assigned to the element, so we never re-assign the same one. */
  const appliedSrcRef = useRef<string | null>(null);
  const pendingSeekRef = useRef<number | null>(null);

  useEffect(() => {
    onEndedRef.current = onEnded;
  }, [onEnded]);

  useEffect(() => {
    onNextTrackRef.current = onNextTrack;
  }, [onNextTrack]);

  useEffect(() => {
    audiobookRef.current = audiobook;
  }, [audiobook]);

  useEffect(() => {
    rateRef.current = playbackRate;
  }, [playbackRate]);

  /**
   * Ref callback that also drives state, so the listener effect below has a
   * dependency that actually changes when the element appears. Reading
   * `audioRef.current` from a dependency array does not work — mutating a ref
   * never schedules a render, so the effect fires at arbitrary times.
   */
  const attachAudio = useCallback((element: HTMLAudioElement | null) => {
    audioRef.current = element;
    setAudioEl(element);
  }, []);

  /**
   * Applies the rate to both `playbackRate` and `defaultPlaybackRate`. Browsers
   * reset `playbackRate` to `defaultPlaybackRate` every time a new resource
   * loads, so setting only the former silently reverts to 1x on the next load.
   */
  const applyPlaybackRate = useCallback((audio: HTMLAudioElement, rate: number) => {
    audio.defaultPlaybackRate = rate;
    if (audio.playbackRate !== rate) {
      audio.playbackRate = rate;
    }
  }, []);

  const savePlaybackPosition = useCallback(async (positionOverride?: number) => {
    const book = audiobookRef.current;
    const audio = audioRef.current;
    if (!book || !audio) return;

    const position = Math.floor(positionOverride ?? audio.currentTime);
    if (!Number.isFinite(position) || position <= 0) return;

    const { error: updateError } = await supabase
      .from('audiobooks')
      .update({ last_playback_position_seconds: position })
      .eq('id', book.id);

    if (updateError) {
      console.error('Error saving playback position:', updateError);
    }
  }, []);

  /**
   * Points the element at `url`, optionally seeking and starting playback.
   *
   * Call this synchronously from a user gesture or from the `ended` handler.
   * Mobile browsers grant autoplay permission per media element based on prior
   * user interaction with *that element*; swapping `src` on the element the user
   * already started keeps the permission, whereas a freshly mounted element gets
   * `NotAllowedError` while the screen is locked.
   */
  const loadSource = useCallback(
    (url: string, options: LoadSourceOptions = {}) => {
      const audio = audioRef.current;
      if (!audio || !url) return;

      const startPlayback = () => {
        applyPlaybackRate(audio, rateRef.current);
        audio.play().catch((err) => {
          console.error('Playback could not be started automatically:', err);
          setIsPlaying(false);
          setIsLoading(false);
        });
      };

      if (appliedSrcRef.current === url) {
        // Already loaded — most often the route catching up with a transition we
        // performed imperatively. Re-assigning src here would restart the part.
        if (options.autoPlay && audio.paused) startPlayback();
        return;
      }

      appliedSrcRef.current = url;
      pendingSeekRef.current =
        options.startAt && options.startAt > 0 ? options.startAt : null;

      setError(null);
      setDuration(0);
      setCurrentTime(options.startAt ?? 0);

      audio.src = url;
      applyPlaybackRate(audio, rateRef.current);
      audio.load();

      if (options.autoPlay) startPlayback();
    },
    [applyPlaybackRate],
  );

  // Audio element event listeners. Keyed on the element itself, which now stays
  // mounted for the lifetime of the page.
  useEffect(() => {
    const audio = audioEl;
    if (!audio) return;

    const handleTimeUpdate = () => {
      if (!isSeekingRef.current) setCurrentTime(audio.currentTime);
    };

    const handleDurationChange = () => {
      setDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
    };

    const handleLoadedMetadata = () => {
      handleDurationChange();
      applyPlaybackRate(audio, rateRef.current);

      const seekTarget = pendingSeekRef.current;
      pendingSeekRef.current = null;
      if (seekTarget == null) return;

      // A position at the very end means the part was played to completion.
      // Resuming there would leave the user staring at a player that cannot
      // advance, so start over instead.
      const finished =
        Number.isFinite(audio.duration) &&
        seekTarget >= audio.duration - END_OF_PART_TOLERANCE_SECONDS;
      audio.currentTime = finished ? 0 : seekTarget;
    };

    const handlePlay = () => {
      applyPlaybackRate(audio, rateRef.current);
      setIsPlaying(true);
      setIsLoading(false);
      setError(null);
    };

    const handlePlaying = () => {
      applyPlaybackRate(audio, rateRef.current);
      setIsPlaying(true);
      setIsLoading(false);
    };

    const handlePause = () => {
      setIsPlaying(false);
      setIsLoading(false);
      void savePlaybackPosition();
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setIsLoading(false);
      void savePlaybackPosition(Math.floor(audio.duration || audio.currentTime));
      // Invoked synchronously inside the media event so that a
      // `loadSource(..., { autoPlay: true })` from the callback still counts as
      // user-activated playback on this element.
      onEndedRef.current?.();
    };

    const handleLoadStart = () => {
      setIsLoading(true);
      setError(null);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
    };

    const handleWaiting = () => {
      setIsLoading(true);
    };

    const handleSeekingEvent = () => {
      isSeekingRef.current = true;
      setIsSeeking(true);
    };

    const handleSeeked = () => {
      isSeekingRef.current = false;
      setIsSeeking(false);
      setCurrentTime(audio.currentTime);
    };

    const handleError = () => {
      setIsLoading(false);
      setIsPlaying(false);
      setError('Failed to load audio file');
      console.error('Audio error:', audio.error);
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('playing', handlePlaying);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('waiting', handleWaiting);
    audio.addEventListener('seeking', handleSeekingEvent);
    audio.addEventListener('seeked', handleSeeked);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('playing', handlePlaying);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('loadstart', handleLoadStart);
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('waiting', handleWaiting);
      audio.removeEventListener('seeking', handleSeekingEvent);
      audio.removeEventListener('seeked', handleSeeked);
      audio.removeEventListener('error', handleError);
    };
  }, [audioEl, applyPlaybackRate, savePlaybackPosition]);

  // React state is the source of truth for rate; push it to the element and
  // remember it for the next visit. Nothing reads the rate back off the element.
  useEffect(() => {
    if (audioEl) applyPlaybackRate(audioEl, playbackRate);
    try {
      window.localStorage.setItem(RATE_STORAGE_KEY, String(playbackRate));
    } catch {
      // Private browsing / storage disabled — the in-memory default still applies.
    }
  }, [audioEl, playbackRate, applyPlaybackRate]);

  useEffect(() => {
    if (audioEl) audioEl.volume = volume;
  }, [audioEl, volume]);

  // Fallback so the play button can never be stuck in a spinner if the browser
  // goes quiet without firing either `canplay` or `error`.
  useEffect(() => {
    if (!isLoading) return;
    const timeout = setTimeout(() => setIsLoading(false), 10000);
    return () => clearTimeout(timeout);
  }, [isLoading]);

  // OS lock-screen / notification controls. Without an active media session the
  // widget goes stale across a part swap, forcing the user to unlock the phone
  // and press play inside the app.
  useEffect(() => {
    const audio = audioEl;
    if (!audio || !('mediaSession' in navigator)) return;

    const { mediaSession } = navigator;
    const nudge = (delta: number) => {
      const target = audio.currentTime + delta;
      audio.currentTime = Math.max(0, Math.min(audio.duration || 0, target));
    };

    mediaSession.setActionHandler('play', () => {
      applyPlaybackRate(audio, rateRef.current);
      audio.play().catch((err) => console.error('Media session play failed:', err));
    });
    mediaSession.setActionHandler('pause', () => audio.pause());
    mediaSession.setActionHandler('seekbackward', (details) =>
      nudge(-(details.seekOffset ?? 15)),
    );
    mediaSession.setActionHandler('seekforward', (details) =>
      nudge(details.seekOffset ?? 15),
    );
    mediaSession.setActionHandler('seekto', (details) => {
      if (details.seekTime != null) audio.currentTime = details.seekTime;
    });
    mediaSession.setActionHandler('nexttrack', () => onNextTrackRef.current?.());

    return () => {
      MEDIA_SESSION_ACTIONS.forEach((action) => {
        try {
          mediaSession.setActionHandler(action, null);
        } catch {
          // Chrome throws for actions it does not support; nothing to undo.
        }
      });
    };
  }, [audioEl, applyPlaybackRate]);

  useEffect(() => {
    if (!('mediaSession' in navigator) || typeof MediaMetadata === 'undefined') return;
    if (!audiobook) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: audiobook.title,
      artist: 'Audio Digest Hub',
    });
  }, [audiobook]);

  useEffect(() => {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.playbackState = isPlaying ? 'playing' : 'paused';
  }, [isPlaying]);

  // Periodic progress checkpoint while playing.
  useEffect(() => {
    if (!audiobook || !isPlaying) return;
    const interval = setInterval(() => void savePlaybackPosition(), 5000);
    return () => clearInterval(interval);
  }, [audiobook, isPlaying, savePlaybackPosition]);

  // Flush progress when the tab is backgrounded or torn down. On mobile the page
  // can be discarded without ever running an unmount.
  useEffect(() => {
    const flush = () => void savePlaybackPosition();
    window.addEventListener('pagehide', flush);
    document.addEventListener('visibilitychange', flush);
    return () => {
      window.removeEventListener('pagehide', flush);
      document.removeEventListener('visibilitychange', flush);
      flush();
    };
  }, [savePlaybackPosition]);

  const togglePlayPause = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (!audio.paused) {
      audio.pause();
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      applyPlaybackRate(audio, rateRef.current);
      await audio.play();
      // Re-assert after play(): some browsers reset the rate when they begin
      // fetching media data for a source that was not preloaded.
      applyPlaybackRate(audio, rateRef.current);
    } catch (err) {
      console.error('Error toggling play/pause:', err);
      setError('Failed to play audio');
    } finally {
      setIsLoading(false);
    }
  }, [applyPlaybackRate]);

  const seekTo = useCallback((time: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    const clamped = Math.max(0, Math.min(audio.duration || 0, time));
    audio.currentTime = clamped;
    setCurrentTime(clamped);
  }, []);

  const skip = useCallback(
    (seconds: number) => {
      const audio = audioRef.current;
      if (!audio) return;
      seekTo(audio.currentTime + seconds);
    },
    [seekTo],
  );

  const handleVolumeChange = useCallback((newVolume: number) => {
    setVolume(newVolume);
  }, []);

  const handlePlaybackRateChange = useCallback((rate: number) => {
    setPlaybackRate(rate);
  }, []);

  return {
    audioRef,
    attachAudio,
    loadSource,
    isPlaying,
    currentTime,
    duration,
    volume,
    playbackRate,
    isLoading,
    error,
    isSeeking,
    togglePlayPause,
    skip,
    seekTo,
    handleVolumeChange,
    handlePlaybackRateChange,
  };
};
