import React, { useEffect, useState, useCallback, useRef } from 'react';
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
import { getSignedAudioUrl } from '@/components/player/signedUrlCache';

interface Audiobook {
  id: string;
  title: string;
  duration_seconds: number;
  last_playback_position_seconds: number;
  storage_path: string;
  chapters_json: Record<string, number> | null;
}

interface NextPart {
  id: string;
  url: string;
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
  // Depend on the id, not the object. supabase-js emits a fresh session (and so
  // a fresh User object) on every token refresh and tab focus; keying effects on
  // the object identity restarted the fetch and stopped playback each time the
  // app came back to the foreground.
  const userId = user?.id ?? null;
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const autoPlay = (location.state as { autoPlay?: boolean })?.autoPlay ?? false;

  const [audiobook, setAudiobook] = useState<Audiobook | null>(null);
  const [audioUrl, setAudioUrl] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [nextPart, setNextPart] = useState<NextPart | null>(null);

  const audiobookRef = useRef<Audiobook | null>(null);
  const nextPartRef = useRef<NextPart | null>(null);
  const pendingAutoPlayRef = useRef(false);

  useEffect(() => {
    audiobookRef.current = audiobook;
  }, [audiobook]);

  useEffect(() => {
    nextPartRef.current = nextPart;
  }, [nextPart]);

  const goToNextPart = useCallback(
    (options: { autoPlay: boolean }) => {
      const next = nextPartRef.current;
      if (!next) return;

      // Swap the source on the element that is already playing, synchronously,
      // before touching the router. Mobile browsers tie autoplay permission to
      // the specific media element the user interacted with, so reusing this one
      // lets part 2 start with the screen still locked. The old flow navigated
      // first, which mounted a brand new <audio> and got NotAllowedError.
      loadSource(next.url, { autoPlay: options.autoPlay, startAt: 0, ownerId: next.id });
      navigate(`/player/${next.id}`, { state: { autoPlay: options.autoPlay } });
    },
    // `loadSource` comes from the hook call below, so it cannot appear in this
    // dependency array — the array is evaluated during render, while the binding
    // is still uninitialised. It is stable for the life of the component, and the
    // body only runs after mount, so closing over it is safe.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [navigate],
  );

  const handleEnded = useCallback(() => {
    const book = audiobookRef.current;
    if (!book || !nextPartRef.current) return;

    const parsed = parseMultiPart(book.title);
    if (!parsed || parsed.part >= parsed.total) return;

    toast({
      title: 'Loading next part',
      description: `${parsed.baseTitle} (Part ${parsed.part + 1} of ${parsed.total})`,
    });
    goToNextPart({ autoPlay: true });
  }, [goToNextPart, toast]);

  const handleNextTrack = useCallback(() => {
    goToNextPart({ autoPlay: true });
  }, [goToNextPart]);

  const {
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
  } = useAudioPlayer(audiobook, handleEnded, handleNextTrack);

  // Fetch metadata + a signed URL for the requested audiobook.
  useEffect(() => {
    if (!id || !userId) return;

    let cancelled = false;
    // Keep whatever is already on screen while the next part resolves — the
    // audio element is playing it, so blanking the UI would flash a spinner
    // over working playback.
    if (!audiobookRef.current) setLoading(true);

    (async () => {
      try {
        const { data, error: fetchError } = await supabase
          .from('audiobooks')
          .select('*')
          .eq('id', id)
          .single();

        if (fetchError) throw fetchError;

        let chaptersData: Record<string, number> | null = null;
        if (data.chapters_json) {
          try {
            chaptersData =
              typeof data.chapters_json === 'string'
                ? JSON.parse(data.chapters_json)
                : (data.chapters_json as Record<string, number>);
          } catch (parseError) {
            console.error('Error parsing chapters_json:', parseError);
          }
        }

        const url = await getSignedAudioUrl(data.storage_path);
        if (cancelled) return;

        setAudiobook({
          id: data.id,
          title: data.title,
          duration_seconds: data.duration_seconds,
          last_playback_position_seconds: data.last_playback_position_seconds || 0,
          storage_path: data.storage_path,
          chapters_json: chaptersData,
        });
        setAudioUrl(url);
      } catch (fetchError) {
        if (cancelled) return;
        console.error('Error fetching audiobook:', fetchError);
        toast({
          title: 'Error',
          description: 'Failed to load audiobook',
          variant: 'destructive',
        });
        navigate('/dashboard');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, userId]);

  // Remember an auto-play request from the route so the load effect below can
  // honour it once the URL for this part is available.
  useEffect(() => {
    if (autoPlay) pendingAutoPlayRef.current = true;
  }, [autoPlay, id]);

  // Hand the resolved URL to the audio element. `loadSource` is a no-op when the
  // element already holds this exact URL, so the router catching up with an
  // in-flight transition does not restart part 2 from the beginning.
  useEffect(() => {
    if (!audioUrl || !audiobook) return;
    const shouldAutoPlay = pendingAutoPlayRef.current;
    pendingAutoPlayRef.current = false;
    loadSource(audioUrl, {
      autoPlay: shouldAutoPlay,
      startAt: audiobook.last_playback_position_seconds,
      ownerId: audiobook.id,
    });
  }, [audioUrl, audiobook, loadSource]);

  // Pre-sign the next part while the current one plays. Signing on `ended`
  // instead would mean awaiting a round trip inside the event handler, which
  // loses the user activation that lets playback continue unattended.
  useEffect(() => {
    if (!audiobook) {
      setNextPart(null);
      return;
    }

    const parsed = parseMultiPart(audiobook.title);
    if (!parsed || parsed.part >= parsed.total) {
      setNextPart(null);
      return;
    }

    const nextTitle = `${parsed.baseTitle} (Part ${parsed.part + 1} of ${parsed.total})`;
    let cancelled = false;

    (async () => {
      try {
        const { data, error: lookupError } = await supabase
          .from('audiobooks')
          .select('id, storage_path')
          .eq('title', nextTitle)
          .maybeSingle();

        if (lookupError) throw lookupError;
        if (!data) {
          if (!cancelled) setNextPart(null);
          return;
        }

        const url = await getSignedAudioUrl(data.storage_path);
        if (!cancelled) setNextPart({ id: data.id, url });
      } catch (lookupError) {
        console.error('Error preparing next part:', lookupError);
        if (!cancelled) setNextPart(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [audiobook]);

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const chapters = Object.entries(audiobook?.chapters_json || {}).sort(([, a], [, b]) => a - b);
  const validChapters = chapters.filter(
    ([, startTime]) => typeof startTime === 'number' && !isNaN(startTime) && isFinite(startTime),
  );
  const multiPart = audiobook ? parseMultiPart(audiobook.title) : null;

  const renderBody = () => {
    if (loading && !audiobook) {
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

    return (
      <div className="px-4 py-6 max-w-4xl mx-auto">
        <Button variant="ghost" onClick={() => navigate('/dashboard')} className="mb-6">
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
                  {nextPart && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => goToNextPart({ autoPlay: isPlaying })}
                    >
                      <SkipForward className="h-4 w-4 mr-1" />
                      Next Part
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
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

  return (
    <>
      {/*
        Deliberately rendered outside every conditional branch and given no `src`
        prop. This element must survive route changes and loading states: if React
        unmounts it, playback stops dead and the replacement element has no
        autoplay permission. The source is assigned imperatively by `loadSource`.
      */}
      <audio ref={attachAudio} preload="auto" />
      {renderBody()}
    </>
  );
};

export default Player;
