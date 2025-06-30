
import React from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Play, Pause, SkipBack, SkipForward, Volume2 } from 'lucide-react';

interface PlayerControlsProps {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  playbackRate: number;
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
  onTogglePlayPause,
  onSkip,
  onSeekTo,
  onVolumeChange,
  onPlaybackRateChange,
  formatTime,
}) => {
  return (
    <div className="space-y-6">
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
          onValueChange={([value]) => onSeekTo(value)}
          className="w-full"
        />
      </div>

      {/* Main Controls */}
      <div className="flex items-center justify-center space-x-4">
        <Button
          variant="outline"
          size="icon"
          onClick={() => onSkip(-15)}
        >
          <SkipBack className="h-4 w-4" />
        </Button>
        
        <Button
          size="icon"
          onClick={onTogglePlayPause}
          className="h-12 w-12"
        >
          {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6" />}
        </Button>
        
        <Button
          variant="outline"
          size="icon"
          onClick={() => onSkip(15)}
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
          />
        </div>
        
        <select
          value={playbackRate}
          onChange={(e) => onPlaybackRateChange(parseFloat(e.target.value))}
          className="px-3 py-1 border rounded-md text-sm"
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
