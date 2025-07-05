
import { useState, useRef, useEffect } from 'react';
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

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateTime = () => setCurrentTime(audio.currentTime);
    const updateDuration = () => setDuration(audio.duration);
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
    };
  }, []);

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

  const togglePlayPause = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
  };

  const skip = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = Math.max(0, Math.min(audio.duration, audio.currentTime + seconds));
  };

  const seekTo = (time: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = time;
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
  };

  return {
    audioRef,
    isPlaying,
    currentTime,
    duration,
    volume,
    playbackRate,
    togglePlayPause,
    skip,
    seekTo,
    handleVolumeChange,
    handlePlaybackRateChange,
    handleLoadedData,
  };
};
