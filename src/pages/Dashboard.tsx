
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Play, Trash2, Clock } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface Audiobook {
  id: string;
  title: string;
  duration_seconds: number;
  last_playback_position_seconds: number;
  created_at: string;
  storage_path: string;
}

const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [audiobooks, setAudiobooks] = useState<Audiobook[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAudiobooks();
  }, [user]);

  const fetchAudiobooks = async () => {
    if (!user) return;

    try {
      const { data, error } = await supabase
        .from('audiobooks')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setAudiobooks(data || []);
    } catch (error) {
      console.error('Error fetching audiobooks:', error);
      toast({
        title: 'Error',
        description: 'Failed to load audiobooks',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const deleteAudiobook = async (audiobook: Audiobook) => {
    if (!confirm('Are you sure you want to delete this audiobook?')) return;

    try {
      // Delete from storage
      const { error: storageError } = await supabase.storage
        .from('audiobooks')
        .remove([audiobook.storage_path]);

      if (storageError) throw storageError;

      // Delete from database
      const { error: dbError } = await supabase
        .from('audiobooks')
        .delete()
        .eq('id', audiobook.id);

      if (dbError) throw dbError;

      setAudiobooks(prev => prev.filter(ab => ab.id !== audiobook.id));
      toast({
        title: 'Success',
        description: 'Audiobook deleted successfully',
      });
    } catch (error) {
      console.error('Error deleting audiobook:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete audiobook',
        variant: 'destructive',
      });
    }
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getProgressPercentage = (current: number, total: number) => {
    return Math.round((current / total) * 100);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Your Audiobook Library</h1>
        <p className="text-gray-600 mt-2">Listen to your daily digest audiobooks</p>
      </div>

      {audiobooks.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No Audiobooks Yet</CardTitle>
            <CardDescription>
              Your generated audiobooks will appear here once your local processor uploads them.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4">
          {audiobooks.map((audiobook) => (
            <Card key={audiobook.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {audiobook.title}
                    </h3>
                    <div className="flex items-center space-x-4 text-sm text-gray-500 mb-3">
                      <span className="flex items-center">
                        <Clock className="h-4 w-4 mr-1" />
                        {formatDuration(audiobook.duration_seconds)}
                      </span>
                      <span>{formatDate(audiobook.created_at)}</span>
                    </div>
                    
                    {audiobook.last_playback_position_seconds > 0 && (
                      <div className="mb-3">
                        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                          <span>Progress</span>
                          <span>{getProgressPercentage(audiobook.last_playback_position_seconds, audiobook.duration_seconds)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{
                              width: `${getProgressPercentage(audiobook.last_playback_position_seconds, audiobook.duration_seconds)}%`
                            }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    <Button
                      onClick={() => navigate(`/player/${audiobook.id}`)}
                      className="flex items-center"
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Listen
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => deleteAudiobook(audiobook)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
