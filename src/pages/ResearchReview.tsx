import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ExternalLink, Check, ChevronLeft, ChevronRight, FlaskConical } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { SUPABASE_URL } from '@/integrations/supabase/client';

interface Paper {
  url: string;
  title: string;
  abstract: string;
  score: number;
  tier: 'deep_dive' | 'summary';
  source: 'arxiv' | 'huggingface';
  clicked: boolean;
}

interface DayData {
  date: string;
  papers: Paper[];
}

const API_URL = `${SUPABASE_URL}/functions/v1`;

const ResearchReview = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(() => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday.toISOString().split('T')[0];
  });
  const [apiKey, setApiKey] = useState('');

  const fetchPapers = useCallback(async () => {
    if (!apiKey) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${API_URL}/research-papers?date=${selectedDate}`,
        {
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data: DayData = await response.json();
      setPapers(data.papers || []);
    } catch (error) {
      console.error('Failed to fetch papers:', error);
      setPapers([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, apiKey]);

  useEffect(() => {
    fetchPapers();
  }, [fetchPapers]);

  // Load API key from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('research_api_key');
    if (stored) {
      setApiKey(stored);
    }
  }, []);

  const saveApiKey = (key: string) => {
    setApiKey(key);
    localStorage.setItem('research_api_key', key);
  };

  const handlePaperClick = async (paper: Paper) => {
    // Open paper in new tab
    window.open(paper.url, '_blank', 'noopener,noreferrer');

    // Mark as clicked via PATCH
    if (apiKey) {
      try {
        await fetch(`${API_URL}/research-papers`, {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            date: selectedDate,
            paper_url: paper.url,
          }),
        });

        // Update local state
        setPapers(prev =>
          prev.map(p =>
            p.url === paper.url ? { ...p, clicked: true } : p
          )
        );
      } catch (error) {
        console.error('Failed to track click:', error);
      }
    }
  };

  const navigateDate = (direction: number) => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() + direction);
    setSelectedDate(date.toISOString().split('T')[0]);
  };

  const summaryPapers = papers.filter(p => p.tier === 'summary');
  const deepDivePapers = papers.filter(p => p.tier === 'deep_dive');

  const getScoreBadgeVariant = (score: number) => {
    if (score >= 8) return 'default';
    if (score >= 5) return 'secondary';
    return 'outline';
  };

  if (!apiKey) {
    return (
      <div className="px-4 py-8 max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <FlaskConical className="h-8 w-8 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Research Review</h1>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Enter API Key</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-600">
              Enter your API key to access research paper data.
            </p>
            <div className="flex gap-2">
              <Input
                type="password"
                placeholder="Your API key"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    saveApiKey((e.target as HTMLInputElement).value);
                  }
                }}
              />
              <Button onClick={(e) => {
                const input = (e.currentTarget.previousElementSibling as HTMLInputElement);
                if (input?.value) saveApiKey(input.value);
              }}>
                Connect
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FlaskConical className="h-8 w-8 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Research Review</h1>
        </div>

        {/* Date navigation */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => navigateDate(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="w-40"
          />
          <Button variant="outline" size="icon" onClick={() => navigateDate(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : papers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-gray-500">
            No research papers processed for {selectedDate}.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {/* Deep-dive papers section */}
          {deepDivePapers.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                Featured Papers ({deepDivePapers.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                {deepDivePapers.map((paper) => (
                  <PaperCard
                    key={paper.url}
                    paper={paper}
                    onClick={() => handlePaperClick(paper)}
                    scoreBadgeVariant={getScoreBadgeVariant(paper.score)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Summary papers section */}
          {summaryPapers.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-gray-800 mb-3">
                Other Papers ({summaryPapers.length})
              </h2>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {summaryPapers.map((paper) => (
                  <PaperCard
                    key={paper.url}
                    paper={paper}
                    onClick={() => handlePaperClick(paper)}
                    scoreBadgeVariant={getScoreBadgeVariant(paper.score)}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
};

interface PaperCardProps {
  paper: Paper;
  onClick: () => void;
  scoreBadgeVariant: 'default' | 'secondary' | 'outline';
}

const PaperCard = ({ paper, onClick, scoreBadgeVariant }: PaperCardProps) => {
  const abstractSnippet = paper.abstract.length > 200
    ? paper.abstract.substring(0, 200) + '...'
    : paper.abstract;

  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-md ${
        paper.clicked ? 'opacity-60 border-green-300' : ''
      }`}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm font-medium leading-tight">
            {paper.title}
          </CardTitle>
          <div className="flex items-center gap-1.5 shrink-0">
            {paper.clicked && (
              <Check className="h-4 w-4 text-green-600" />
            )}
            <Badge variant={scoreBadgeVariant} className="text-xs">
              {paper.score}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="text-xs text-gray-600 mb-2">{abstractSnippet}</p>
        <div className="flex items-center justify-between">
          <Badge variant="outline" className="text-xs">
            {paper.source === 'arxiv' ? 'Arxiv' : 'HuggingFace'}
          </Badge>
          <ExternalLink className="h-3.5 w-3.5 text-gray-400" />
        </div>
      </CardContent>
    </Card>
  );
};

export default ResearchReview;
