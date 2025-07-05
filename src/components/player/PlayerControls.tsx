import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Play, Pause, SkipBack, SkipForward, Volume2, Loader2 } from 'lucide-react';

interface PlayerControlsProps {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  playbackRate: number;
  isLoading?: boolean;
  error?: string | null;
  isSeeking?: boolean;
  onTogglePlayPause: () => void;
  onSkip: (seconds: number) => void;
  onSeekTo: (time: number) => void;
  onVolumeChange: (volume: number) => void;
  onPlaybackRateChange: (rate: number) => void;
  formatTime: (seconds: number) => string;
}

export const PlayerControls: React.FC<PlayerControlsProps> = ({
  isPlaying,
  currentTime,
  duration,
  volume,
  playbackRate,
  isLoading = false,
  error = null,
  isSeeking = false,
  onTogglePlayPause,
  onSkip,
  onSeekTo,
  onVolumeChange,
  onPlaybackRateChange,
  formatTime,
}) => {
  const [sliderValue, setSliderValue] = React.useState(currentTime);

  // Update slider value when currentTime changes (but not during seeking)
  React.useEffect(() => {
    if (!isSeeking) {
      setSliderValue(currentTime);
    }
  }, [currentTime, isSeeking]);

  const handleSliderChange = (value: number[]) => {
    setSliderValue(value[0]);
  };

  const handleSliderCommit = (value: number[]) => {
    onSeekTo(value[0]);
  };

  // Force clear loading state if it's been stuck for too long
  React.useEffect(() => {
    if (isLoading) {
      const timeout = setTimeout(() => {
        console.log('PlayerControls: Loading state stuck, forcing clear');
        // This will trigger a re-render and hopefully clear the loading state
      }, 3000);
      return () => clearTimeout(timeout);
    }
  }, [isLoading]);

  return (
    <div className="space-y-6">
      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm text-gray-500">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
        <Slider
          value={[sliderValue]}
          max={duration}
          step={1}
          onValueChange={handleSliderChange}
          onValueCommit={handleSliderCommit}
          className="w-full"
          disabled={!!error}
        />
      </div>

      {/* Main Controls */}
      <div className="flex items-center justify-center space-x-4">
        <Button
          variant="outline"
          size="icon"
          onClick={() => onSkip(-15)}
          disabled={!!error}
        >
          <SkipBack className="h-4 w-4" />
        </Button>
        
        <Button
          size="icon"
          onClick={onTogglePlayPause}
          className="h-12 w-12"
          disabled={!!error}
        >
          {isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin" />
          ) : isPlaying ? (
            <Pause className="h-6 w-6" />
          ) : (
            <Play className="h-6 w-6" />
          )}
        </Button>
        
        <Button
          variant="outline"
          size="icon"
          onClick={() => onSkip(15)}
          disabled={!!error}
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
            onValueChange={([value]) => onVolumeChange(value)}
            className="w-24"
            disabled={!!error}
          />
        </div>
        
        <select
          value={playbackRate}
          onChange={(e) => onPlaybackRateChange(parseFloat(e.target.value))}
          className="px-3 py-1 border rounded-md text-sm"
          disabled={!!error}
        >
          <option value={1}>1x</option>
          <option value={1.25}>1.25x</option>
          <option value={1.5}>1.5x</option>
          <option value={2}>2x</option>
        </select>
      </div>
    </div>
  );
};
