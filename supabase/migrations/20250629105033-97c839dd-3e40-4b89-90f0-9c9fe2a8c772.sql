
-- Create newsletter_sources table
CREATE TABLE public.newsletter_sources (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  sender_email TEXT NOT NULL,
  custom_name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create audiobooks table
CREATE TABLE public.audiobooks (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  title TEXT NOT NULL,
  duration_seconds INTEGER NOT NULL,
  storage_path TEXT NOT NULL,
  chapters_json JSONB,
  last_playback_position_seconds INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create API keys table for secure API access
CREATE TABLE public.api_keys (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  name TEXT DEFAULT 'Default API Key',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  last_used_at TIMESTAMP WITH TIME ZONE
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.newsletter_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audiobooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

-- Create policies for newsletter_sources
CREATE POLICY "Users can view their own newsletter sources" 
  ON public.newsletter_sources 
  FOR SELECT 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own newsletter sources" 
  ON public.newsletter_sources 
  FOR INSERT 
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own newsletter sources" 
  ON public.newsletter_sources 
  FOR DELETE 
  USING (auth.uid() = user_id);

-- Create policies for audiobooks
CREATE POLICY "Users can view their own audiobooks" 
  ON public.audiobooks 
  FOR SELECT 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own audiobooks" 
  ON public.audiobooks 
  FOR INSERT 
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own audiobooks" 
  ON public.audiobooks 
  FOR UPDATE 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own audiobooks" 
  ON public.audiobooks 
  FOR DELETE 
  USING (auth.uid() = user_id);

-- Create policies for API keys
CREATE POLICY "Users can view their own API keys" 
  ON public.api_keys 
  FOR SELECT 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own API keys" 
  ON public.api_keys 
  FOR INSERT 
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own API keys" 
  ON public.api_keys 
  FOR DELETE 
  USING (auth.uid() = user_id);

-- Create storage bucket for audiobooks
INSERT INTO storage.buckets (id, name, public) 
VALUES ('audiobooks', 'audiobooks', false);

-- Create storage policy for audiobooks bucket
CREATE POLICY "Users can upload their own audiobooks"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'audiobooks' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can view their own audiobooks"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'audiobooks' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete their own audiobooks"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'audiobooks' AND auth.uid()::text = (storage.foldername(name))[1]);
