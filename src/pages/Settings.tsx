
import React, { useEffect, useState } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Trash2, Plus, Key } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface NewsletterSource {
  id: string;
  sender_email: string;
  custom_name: string;
}

interface ApiKey {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
}

const Settings = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [sources, setSources] = useState<NewsletterSource[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [newSource, setNewSource] = useState({ sender_email: '', custom_name: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSources();
    fetchApiKeys();
  }, [user]);

  const fetchSources = async () => {
    if (!user) return;

    try {
      const { data, error } = await supabase
        .from('newsletter_sources')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setSources(data || []);
    } catch (error) {
      console.error('Error fetching sources:', error);
      toast({
        title: 'Error',
        description: 'Failed to load newsletter sources',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchApiKeys = async () => {
    if (!user) return;

    try {
      const { data, error } = await supabase
        .from('api_keys')
        .select('id, name, created_at, last_used_at')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setApiKeys(data || []);
    } catch (error) {
      console.error('Error fetching API keys:', error);
    }
  };

  const addSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !newSource.sender_email || !newSource.custom_name) return;

    try {
      const { error } = await supabase
        .from('newsletter_sources')
        .insert([{
          user_id: user.id,
          sender_email: newSource.sender_email,
          custom_name: newSource.custom_name,
        }]);

      if (error) throw error;

      setNewSource({ sender_email: '', custom_name: '' });
      fetchSources();
      toast({
        title: 'Success',
        description: 'Newsletter source added successfully',
      });
    } catch (error) {
      console.error('Error adding source:', error);
      toast({
        title: 'Error',
        description: 'Failed to add newsletter source',
        variant: 'destructive',
      });
    }
  };

  const deleteSource = async (id: string) => {
    if (!confirm('Are you sure you want to delete this newsletter source?')) return;

    try {
      const { error } = await supabase
        .from('newsletter_sources')
        .delete()
        .eq('id', id);

      if (error) throw error;

      setSources(prev => prev.filter(source => source.id !== id));
      toast({
        title: 'Success',
        description: 'Newsletter source deleted successfully',
      });
    } catch (error) {
      console.error('Error deleting source:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete newsletter source',
        variant: 'destructive',
      });
    }
  };

  const generateApiKey = async () => {
    if (!user) return;

    try {
      // Generate a random API key
      const apiKey = `dda_${Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, '0')).join('')}`;
      
      // Hash the key for storage
      const encoder = new TextEncoder();
      const data = encoder.encode(apiKey);
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const keyHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

      const { error } = await supabase
        .from('api_keys')
        .insert([{
          user_id: user.id,
          key_hash: keyHash,
          name: 'API Key',
        }]);

      if (error) throw error;

      fetchApiKeys();
      
      // Show the key to the user (only time they'll see it)
      toast({
        title: 'API Key Generated',
        description: `Your API key: ${apiKey}. Save this key - you won't see it again!`,
      });
    } catch (error) {
      console.error('Error generating API key:', error);
      toast({
        title: 'Error',
        description: 'Failed to generate API key',
        variant: 'destructive',
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-2">Manage your newsletter sources and API keys</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>User Information</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">Email: {user?.email}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Newsletter Sources</CardTitle>
          <CardDescription>
            Add email addresses from newsletters you want to convert to audio
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={addSource} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="sender_email">Sender Email</Label>
              <Input
                id="sender_email"
                type="email"
                value={newSource.sender_email}
                onChange={(e) => setNewSource(prev => ({ ...prev, sender_email: e.target.value }))}
                placeholder="newsletter@example.com"
                required
              />
            </div>
            <div>
              <Label htmlFor="custom_name">Custom Name</Label>
              <Input
                id="custom_name"
                value={newSource.custom_name}
                onChange={(e) => setNewSource(prev => ({ ...prev, custom_name: e.target.value }))}
                placeholder="My Newsletter"
                required
              />
            </div>
            <div className="flex items-end">
              <Button type="submit" className="w-full">
                <Plus className="h-4 w-4 mr-2" />
                Add Source
              </Button>
            </div>
          </form>

          {sources.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-medium">Current Sources</h4>
              {sources.map((source) => (
                <div key={source.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">{source.custom_name}</p>
                    <p className="text-sm text-gray-600">{source.sender_email}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => deleteSource(source.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>
            Generate API keys for your local processor application
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={generateApiKey}>
            <Key className="h-4 w-4 mr-2" />
            Generate New API Key
          </Button>

          {apiKeys.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-medium">Active API Keys</h4>
              {apiKeys.map((key) => (
                <div key={key.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">{key.name}</p>
                    <p className="text-sm text-gray-600">
                      Created: {new Date(key.created_at).toLocaleDateString()}
                      {key.last_used_at && ` • Last used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Settings;
