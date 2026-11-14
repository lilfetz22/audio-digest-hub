import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { SUPABASE_URL } from '@/integrations/supabase/client';

type TtsStatus = 'queued' | 'starting' | 'synthesizing' | 'uploading' | 'done' | 'failed';

interface TtsJob {
  id: string;
  title: string | null;
  status: TtsStatus;
  percent: number;
  error: string | null;
  created_at: string;
  updated_at: string;
}

const API_URL = `${SUPABASE_URL}/functions/v1`;
const POLL_INTERVAL_MS = 10000;

const STATUS_LABELS: Record<TtsStatus, string> = {
  queued: 'Queued',
  starting: 'Starting',
  synthesizing: 'Synthesizing',
  uploading: 'Uploading',
  done: 'Done',
  failed: 'Failed',
};

const isTerminal = (status: TtsStatus) => status === 'done' || status === 'failed';

const TextToSpeech = () => {
  const { session } = useAuth();
  const { toast } = useToast();
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [jobs, setJobs] = useState<TtsJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const token = session?.access_token;

  const fetchJobs = useCallback(async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/tts-jobs`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const data: TtsJob[] = await response.json();
      setJobs(data);
    } catch (error) {
      console.error('Error fetching TTS jobs:', error);
      toast({
        title: 'Error',
        description: 'Failed to load jobs',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [token, toast]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const hasActive = jobs.some((job) => !isTerminal(job.status));

  useEffect(() => {
    const refreshIfVisible = () => {
      if (document.visibilityState === 'visible') fetchJobs();
    };

    const interval = hasActive
      ? window.setInterval(refreshIfVisible, POLL_INTERVAL_MS)
      : undefined;

    document.addEventListener('visibilitychange', refreshIfVisible);
    window.addEventListener('focus', refreshIfVisible);

    return () => {
      if (interval !== undefined) window.clearInterval(interval);
      document.removeEventListener('visibilitychange', refreshIfVisible);
      window.removeEventListener('focus', refreshIfVisible);
    };
  }, [hasActive, fetchJobs]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || submitting || !token) return;

    setSubmitting(true);
    try {
      const trimmedTitle = title.trim();
      const response = await fetch(`${API_URL}/tts-jobs`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          ...(trimmedTitle ? { title: trimmedTitle } : {}),
        }),
      });

      if (!response.ok) {
        const body: { error?: string } = await response.json().catch(() => ({}));
        throw new Error(body.error || `Request failed (${response.status})`);
      }

      const created: { id: string; status: TtsStatus } = await response.json();
      const now = new Date().toISOString();
      setJobs((prev) => [
        {
          id: created.id,
          title: trimmedTitle || null,
          status: created.status,
          percent: 0,
          error: null,
          created_at: now,
          updated_at: now,
        },
        ...prev.filter((job) => job.id !== created.id),
      ]);
      setText('');
      setTitle('');
    } catch (error) {
      console.error('Error creating TTS job:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to create audio',
        variant: 'destructive',
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="px-4 py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Text to Speech</h1>
        <p className="text-gray-600 mt-2">Paste text and get an MP3 added to your library.</p>
      </div>

      <Card className="mb-6">
        <CardContent className="p-4 sm:p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Textarea
              rows={10}
              placeholder="Paste your text here"
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="min-h-[240px]"
            />
            <Input
              placeholder="Title (optional)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Button
              type="submit"
              disabled={!text.trim() || submitting}
              className="w-full sm:w-auto"
            >
              {submitting ? 'Submitting...' : 'Create audio'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent jobs</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : jobs.length === 0 ? (
            <p className="text-sm text-gray-500">No jobs yet.</p>
          ) : (
            <ul className="space-y-4">
              {jobs.map((job) => (
                <li key={job.id} className="border-b last:border-b-0 pb-4 last:pb-0">
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="font-medium text-gray-900 truncate">
                      {job.title || 'Untitled'}
                    </span>
                    <span className="text-sm text-gray-500 shrink-0">
                      {STATUS_LABELS[job.status]}
                    </span>
                  </div>
                  {!isTerminal(job.status) && (
                    <div className="space-y-1">
                      <Progress value={job.percent} />
                      <p className="text-xs text-gray-500">{job.percent}%</p>
                    </div>
                  )}
                  {job.status === 'failed' && (
                    <p className="text-sm text-destructive break-words">
                      {job.error || 'Job failed'}
                    </p>
                  )}
                  {job.status === 'done' && (
                    <p className="text-sm text-gray-600">
                      Ready — find it in your{' '}
                      <Link to="/dashboard" className="text-blue-600 underline">
                        Library
                      </Link>
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default TextToSpeech;
