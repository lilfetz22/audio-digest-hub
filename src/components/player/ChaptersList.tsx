
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ChaptersListProps {
  chapters: [string, number][];
  currentTime: number;
  onJumpToChapter: (startTime: number) => void;
  formatTime: (seconds: number) => string;
}

export const ChaptersList: React.FC<ChaptersListProps> = ({
  chapters,
  currentTime,
  onJumpToChapter,
  formatTime,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Chapters</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {chapters.map(([title, startTime]) => (
            <button
              key={title}
              onClick={() => onJumpToChapter(startTime)}
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
  );
};
