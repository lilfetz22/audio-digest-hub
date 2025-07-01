
import React, { useEffect, useState } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/use-toast';
import { ApiKeyModal } from '@/components/ui/api-key-modal';
import { UserInfoCard } from '@/components/settings/UserInfoCard';
import { NewsletterSourcesCard } from '@/components/settings/NewsletterSourcesCard';
import { ApiKeysCard } from '@/components/settings/ApiKeysCard';

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
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [generatedApiKey, setGeneratedApiKey] = useState('');

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
      const apiKey = `dda_${Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, '0')).join('')}`;
      
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
      setGeneratedApiKey(apiKey);
      setShowApiKeyModal(true);
    } catch (error) {
      console.error('Error generating API key:', error);
      toast({
        title: 'Error',
        description: 'Failed to generate API key',
        variant: 'destructive',
      });
    }
  };

  const deleteApiKey = async (id: string) => {
    if (!confirm('Are you sure you want to delete this API key? This action cannot be undone.')) return;

    try {
      const { error } = await supabase
        .from('api_keys')
        .delete()
        .eq('id', id);

      if (error) throw error;

      setApiKeys(prev => prev.filter(key => key.id !== id));
      toast({
        title: 'Success',
        description: 'API key deleted successfully',
      });
    } catch (error) {
      console.error('Error deleting API key:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete API key',
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

      <UserInfoCard user={user} />

      <NewsletterSourcesCard
        sources={sources}
        newSource={newSource}
        setNewSource={setNewSource}
        onAddSource={addSource}
        onDeleteSource={deleteSource}
      />

      <ApiKeysCard
        apiKeys={apiKeys}
        onGenerateApiKey={generateApiKey}
        onDeleteApiKey={deleteApiKey}
      />

      <ApiKeyModal
        isOpen={showApiKeyModal}
        onClose={() => setShowApiKeyModal(false)}
        apiKey={generatedApiKey}
      />
    </div>
  );
};

export default Settings;
