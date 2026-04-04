import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, SkipForward } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { PlayerControls } from '@/components/player/PlayerControls';
import { ChaptersList } from '@/components/player/ChaptersList';
import { useAudioPlayer } from '@/components/player/useAudioPlayer';

interface Audiobook {
  id: string;
  title: string;
  duration_seconds: number;
  last_playback_position_seconds: number;
  storage_path: string;
  chapters_json: Record<string, number> | null;
}

/** Parse "Part X of Y" from a title like "Daily Digest for 2026-04-02 (Part 1 of 4)" */
function parseMultiPart(title: string): { baseTitle: string; part: number; total: number } | null {
  const match = title.match(/^(.+?)\s*\(Part (\d+) of (\d+)\)\s*$/i);
  if (!match) return null;
  return { baseTitle: match[1].trim(), part: parseInt(match[2], 10), total: parseInt(match[3], 10) };
}

const Player = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const autoPlay = (location.state as { autoPlay?: boolean })?.autoPlay ?? false;
  const [audiobook, setAudiobook] = useState<Audiobook | null>(null);
  const [audioUrl, setAudioUrl] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [nextPartId, setNextPartId] = useState<string | null>(null);

  const handleEnded = useCallback(async () => {
    if (!audiobook) return;
    const parsed = parseMultiPart(audiobook.title);
    if (!parsed || parsed.part >= parsed.total) return;

    const nextTitle = `${parsed.baseTitle} (Part ${parsed.part + 1} of ${parsed.total})`;
    try {
      const { data } = await supabase
        .from('audiobooks')
        .select('id')
        .eq('title', nextTitle)
        .maybeSingle();

      if (data) {
        toast({ title: 'Loading next part', description: nextTitle });
        navigate(`/player/${data.id}`, { state: { autoPlay: true } });
      }
    } catch (err) {
      console.error('Error finding next part:', err);
    }
  }, [audiobook, navigate, toast]);

  const {
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
  } = useAudioPlayer(audiobook, handleEnded);

  useEffect(() => {
    if (id) {
      fetchAudiobook();
    }
  }, [id, user]);

  // Auto-play when navigating from a completed previous part
  useEffect(() => {
    if (autoPlay && audioUrl && audioRef.current) {
      const audio = audioRef.current;
      const tryAutoPlay = () => {
        audio.play().catch((err) => console.error('Auto-play failed:', err));
        audio.removeEventListener('canplay', tryAutoPlay);
      };
      if (audio.readyState >= 3) {
        audio.play().catch((err) => console.error('Auto-play failed:', err));
      } else {
        audio.addEventListener('canplay', tryAutoPlay);
        return () => audio.removeEventListener('canplay', tryAutoPlay);
      }
    }
  }, [autoPlay, audioUrl]);

  // Look up the next part ID for the UI "Next Part" button
  useEffect(() => {
    if (!audiobook) { setNextPartId(null); return; }
    const parsed = parseMultiPart(audiobook.title);
    if (!parsed || parsed.part >= parsed.total) { setNextPartId(null); return; }

    const nextTitle = `${parsed.baseTitle} (Part ${parsed.part + 1} of ${parsed.total})`;
    supabase
      .from('audiobooks')
      .select('id')
      .eq('title', nextTitle)
      .maybeSingle()
      .then(({ data }) => setNextPartId(data?.id ?? null));
  }, [audiobook]);

  const fetchAudiobook = async () => {
    if (!user || !id) return;

    try {
      const { data, error } = await supabase
        .from('audiobooks')
        .select('*')
        .eq('id', id)
        .single();

      if (error) throw error;
      
      // Parse chapters_json if it's a string
      let chaptersData: Record<string, number> | null = null;
      if (data.chapters_json) {
        try {
          if (typeof data.chapters_json === 'string') {
            chaptersData = JSON.parse(data.chapters_json);
          } else {
            chaptersData = data.chapters_json as Record<string, number>;
          }
        } catch (parseError) {
          console.error('Error parsing chapters_json:', parseError);
          chaptersData = null;
        }
      }
      
      const transformedData: Audiobook = {
        id: data.id,
        title: data.title,
        duration_seconds: data.duration_seconds,
        last_playback_position_seconds: data.last_playback_position_seconds || 0,
        storage_path: data.storage_path,
        chapters_json: chaptersData
      };
      
      setAudiobook(transformedData);

      const { data: urlData, error: urlError } = await supabase.storage
        .from('audiobooks')
        .createSignedUrl(data.storage_path, 3600);

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

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
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

  // Debug logging for chapters
  console.log('Chapters data:', audiobook.chapters_json);
  console.log('Parsed chapters:', chapters);

  // Filter out invalid chapters (where startTime is not a valid number)
  const validChapters = chapters.filter(([, startTime]) => 
    typeof startTime === 'number' && !isNaN(startTime) && isFinite(startTime)
  );

  const multiPart = parseMultiPart(audiobook.title);

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
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl">{audiobook.title}</CardTitle>
                  {multiPart && (
                    <p className="text-sm text-gray-500 mt-1">
                      {multiPart.part < multiPart.total
                        ? 'Next part will play automatically when this one ends.'
                        : 'This is the final part.'}
                    </p>
                  )}
                </div>
                {nextPartId && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/player/${nextPartId}`)}
                  >
                    <SkipForward className="h-4 w-4 mr-1" />
                    Next Part
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <audio
                ref={audioRef}
                src={audioUrl}
                onLoadedData={handleLoadedData}
                preload="metadata"
                controls={false}
                onPlay={() => console.log('Audio onPlay event')}
                onPause={() => console.log('Audio onPause event')}
                onLoadStart={() => console.log('Audio onLoadStart event')}
                onCanPlay={() => console.log('Audio onCanPlay event')}
                onError={(e) => console.log('Audio onError event', e)}
                onWaiting={() => console.log('Audio onWaiting event')}
                onPlaying={() => console.log('Audio onPlaying event')}
              />

              <PlayerControls
                isPlaying={isPlaying}
                currentTime={currentTime}
                duration={duration}
                volume={volume}
                playbackRate={playbackRate}
                isLoading={isLoading}
                error={error}
                isSeeking={isSeeking}
                onTogglePlayPause={togglePlayPause}
                onSkip={skip}
                onSeekTo={seekTo}
                onVolumeChange={handleVolumeChange}
                onPlaybackRateChange={handlePlaybackRateChange}
                formatTime={formatTime}
              />
            </CardContent>
          </Card>
        </div>

        <div>
          <ChaptersList
            chapters={validChapters}
            currentTime={currentTime}
            onJumpToChapter={seekTo}
            formatTime={formatTime}
          />
        </div>
      </div>
    </div>
  );
};

export default Player;
