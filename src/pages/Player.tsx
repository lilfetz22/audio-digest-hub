
import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Play, Pause, SkipBack, SkipForward, ArrowLeft, Volume2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface Audiobook {
  id: string;
  title: string;
  duration_seconds: number;
  last_playback_position_seconds: number;
  storage_path: string;
  chapters_json: Record<string, number> | null;
}

const Player = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const audioRef = useRef<HTMLAudioElement>(null);
  const [audiobook, setAudiobook] = useState<Audiobook | null>(null);
  const [audioUrl, setAudioUrl] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchAudiobook();
    }
  }, [id, user]);

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
  }, [audioUrl]);

  // Save playback position every 5 seconds
  useEffect(() => {
    if (!audiobook || !isPlaying) return;

    const interval = setInterval(() => {
      savePlaybackPosition();
    }, 5000);

    return () => clearInterval(interval);
  }, [audiobook, isPlaying, currentTime]);

  const fetchAudiobook = async () => {
    if (!user || !id) return;

    try {
      const { data, error } = await supabase
        .from('audiobooks')
        .select('*')
        .eq('id', id)
        .single();

      if (error) throw error;
      
      // Transform the data to match our interface
      const transformedData: Audiobook = {
        id: data.id,
        title: data.title,
        duration_seconds: data.duration_seconds,
        last_playback_position_seconds: data.last_playback_position_seconds || 0,
        storage_path: data.storage_path,
        chapters_json: data.chapters_json as Record<string, number> | null
      };
      
      setAudiobook(transformedData);

      // Get signed URL for the audio file
      const { data: urlData, error: urlError } = await supabase.storage
        .from('audiobooks')
        .createSignedUrl(data.storage_path, 3600); // 1 hour expiry

      if (urlError) throw urlError;
      
      setAudioUrl(urlData.signedUrl);
    } catch (error) {
      console.error('Error fetching audiobook:', error);
      toast({
        title: 'Error',
        description: 'Failed to load audiobook',
        variant: 'destructive',
      });
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

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

  const jumpToChapter = (startTime: number) => {
    seekTo(startTime);
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // Set initial playback position when audio loads
  const handleLoadedData = () => {
    if (audiobook && audiobook.last_playback_position_seconds > 0) {
      seekTo(audiobook.last_playback_position_seconds);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!audiobook || !audioUrl) {
    return (
      <div className="text-center py-12">
        <p>Audiobook not found</p>
        <Button onClick={() => navigate('/dashboard')} className="mt-4">
          Back to Library
        </Button>
      </div>
    );
  }

  const chapters = Object.entries(audiobook.chapters_json || {}).sort(([, a], [, b]) => a - b);

  return (
    <div className="px-4 py-6 max-w-4xl mx-auto">
      <Button
        variant="ghost"
        onClick={() => navigate('/dashboard')}
        className="mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Library
      </Button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">{audiobook.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <audio
                ref={audioRef}
                src={audioUrl}
                onLoadedData={handleLoadedData}
                onVolumeChange={(e) => setVolume((e.target as HTMLAudioElement).volume)}
                onRateChange={(e) => setPlaybackRate((e.target as HTMLAudioElement).playbackRate)}
              />

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-gray-500">
                  <span>{formatTime(currentTime)}</span>
                  <span>{formatTime(duration)}</span>
                </div>
                <Slider
                  value={[currentTime]}
                  max={duration}
                  step={1}
                  onValueChange={([value]) => seekTo(value)}
                  className="w-full"
                />
              </div>

              {/* Controls */}
              <div className="flex items-center justify-center space-x-4">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => skip(-15)}
                >
                  <SkipBack className="h-4 w-4" />
                </Button>
                
                <Button
                  size="icon"
                  onClick={togglePlayPause}
                  className="h-12 w-12"
                >
                  {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6" />}
                </Button>
                
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => skip(15)}
                >
                  <SkipForward className="h-4 w-4" />
                </Button>
              </div>

              {/* Additional Controls */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Volume2 className="h-4 w-4" />
                  <Slider
                    value={[volume]}
                    max={1}
                    step={0.1}
                    onValueChange={([value]) => {
                      setVolume(value);
                      if (audioRef.current) {
                        audioRef.current.volume = value;
                      }
                    }}
                    className="w-24"
                  />
                </div>
                
                <select
                  value={playbackRate}
                  onChange={(e) => {
                    const rate = parseFloat(e.target.value);
                    setPlaybackRate(rate);
                    if (audioRef.current) {
                      audioRef.current.playbackRate = rate;
                    }
                  }}
                  className="px-3 py-1 border rounded-md text-sm"
                >
                  <option value={1}>1x</option>
                  <option value={1.25}>1.25x</option>
                  <option value={1.5}>1.5x</option>
                  <option value={2}>2x</option>
                </select>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Chapters */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Chapters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {chapters.map(([title, startTime]) => (
                  <button
                    key={title}
                    onClick={() => jumpToChapter(startTime)}
                    className={`w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors ${
                      currentTime >= startTime && 
                      (chapters[chapters.indexOf([title, startTime]) + 1]?.[1] || Infinity) > currentTime
                        ? 'bg-blue-50 border-l-4 border-blue-500'
                        : ''
                    }`}
                  >
                    <div className="font-medium text-sm">{title}</div>
                    <div className="text-xs text-gray-500">{formatTime(startTime)}</div>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Player;
