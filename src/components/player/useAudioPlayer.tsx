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

export const useAudioPlayer = (audiobook: Audiobook | null) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(2);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSeeking, setIsSeeking] = useState(false);

  // Sync state with audio element
  const syncAudioState = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    setIsPlaying(!audio.paused);
    setCurrentTime(audio.currentTime);
    setDuration(audio.duration || 0);
    setVolume(audio.volume);
    setPlaybackRate(audio.playbackRate);
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => {
      if (!isSeeking) {
        setCurrentTime(audio.currentTime);
      }
    };
    
    const updateDuration = () => {
      setDuration(audio.duration || 0);
    };
    
    const handlePlay = () => {
      setIsPlaying(true);
      setError(null);
    };
    
    const handlePause = () => {
      setIsPlaying(false);
    };
    
    const handleEnded = () => {
      setIsPlaying(false);
    };

    const handleLoadStart = () => {
      setIsLoading(true);
      setError(null);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
      syncAudioState();
    };

    const handleError = (e: Event) => {
      setIsLoading(false);
      setIsPlaying(false);
      setError('Failed to load audio file');
      console.error('Audio error:', e);
    };

    const handleWaiting = () => {
      setIsLoading(true);
    };

    const handleSeeking = () => {
      setIsSeeking(true);
    };

    const handleSeeked = () => {
      setIsSeeking(false);
      setCurrentTime(audio.currentTime);
    };

    // Add all event listeners
    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('loadeddata', updateDuration);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('error', handleError);
    audio.addEventListener('waiting', handleWaiting);
    audio.addEventListener('seeking', handleSeeking);
    audio.addEventListener('seeked', handleSeeked);

    // Initial sync
    syncAudioState();

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('loadeddata', updateDuration);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('loadstart', handleLoadStart);
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('waiting', handleWaiting);
      audio.removeEventListener('seeking', handleSeeking);
      audio.removeEventListener('seeked', handleSeeked);
    };
  }, [audiobook, syncAudioState, isSeeking]);

  // Save playback position every 5 seconds when playing
  useEffect(() => {
    if (!audiobook || !isPlaying || !audioRef.current) return;

    const interval = setInterval(() => {
      savePlaybackPosition();
    }, 5000);

    return () => clearInterval(interval);
  }, [audiobook, isPlaying]);

  // Save position when pausing or component unmounts
  useEffect(() => {
    return () => {
      if (audiobook && audioRef.current && audioRef.current.currentTime > 0) {
        savePlaybackPosition();
      }
    };
  }, [audiobook]);

  const savePlaybackPosition = async () => {
    if (!audiobook || !audioRef.current) return;

    try {
      await supabase
        .from('audiobooks')
        .update({ last_playback_position_seconds: Math.floor(audioRef.current.currentTime) })
        .eq('id', audiobook.id);
    } catch (error) {
      console.error('Error saving playback position:', error);
    }
  };

  const togglePlayPause = async () => {
    const audio = audioRef.current;
    if (!audio) return;

    try {
      if (isPlaying) {
        audio.pause();
      } else {
        setIsLoading(true);
        await audio.play();
      }
    } catch (error) {
      console.error('Error toggling play/pause:', error);
      setError('Failed to play audio');
      setIsLoading(false);
    }
  };

  const skip = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newTime = Math.max(0, Math.min(audio.duration || 0, audio.currentTime + seconds));
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const seekTo = (time: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    const clampedTime = Math.max(0, Math.min(audio.duration || 0, time));
    audio.currentTime = clampedTime;
    setCurrentTime(clampedTime);
  };

  const handleVolumeChange = (newVolume: number) => {
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const handlePlaybackRateChange = (rate: number) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  const handleLoadedData = () => {
    const audio = audioRef.current;
    if (!audio) return;
    
    // Set playback rate to match state
    audio.playbackRate = playbackRate;
    
    // Restore playback position
    if (audiobook && audiobook.last_playback_position_seconds > 0) {
      seekTo(audiobook.last_playback_position_seconds);
    }
    
    // Sync state after loading
    syncAudioState();
  };

  return {
    audioRef,
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
    handleLoadedData,
  };
};
