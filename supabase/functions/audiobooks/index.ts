
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  if (req.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Get API key from header
    const authHeader = req.headers.get('Authorization')
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(
        JSON.stringify({ error: 'Missing or invalid authorization header' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const apiKey = authHeader.substring(7) // Remove 'Bearer '
    
    // Hash the provided key to compare with stored hash
    const encoder = new TextEncoder()
    const data = encoder.encode(apiKey)
    const hashBuffer = await crypto.subtle.digest('SHA-256', data)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    const keyHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')

    // Find the API key and get user_id
    const { data: apiKeyData, error: apiKeyError } = await supabaseClient
      .from('api_keys')
      .select('user_id')
      .eq('key_hash', keyHash)
      .single()

    if (apiKeyError || !apiKeyData) {
      return new Response(
        JSON.stringify({ error: 'Invalid API key' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Update last_used_at
    await supabaseClient
      .from('api_keys')
      .update({ last_used_at: new Date().toISOString() })
      .eq('key_hash', keyHash)

    // Parse multipart form data
    const formData = await req.formData()
    const audioFile = formData.get('audio_file') as File
    const metadataString = formData.get('metadata') as string

    if (!audioFile || !metadataString) {
      return new Response(
        JSON.stringify({ error: 'Missing audio_file or metadata' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Parse metadata
    let metadata
    try {
      metadata = JSON.parse(metadataString)
    } catch (error) {
      return new Response(
        JSON.stringify({ error: 'Invalid metadata JSON' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Generate unique file path
    const audioBookId = crypto.randomUUID()
    const filePath = `${apiKeyData.user_id}/${audioBookId}.mp3`

    // Upload file to storage
    const { error: uploadError } = await supabaseClient.storage
      .from('audiobooks')
      .upload(filePath, audioFile, {
        contentType: 'audio/mpeg',
        upsert: false
      })

    if (uploadError) {
      console.error('Upload error:', uploadError)
      return new Response(
        JSON.stringify({ error: 'Failed to upload audio file' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Insert audiobook record
    const { error: dbError } = await supabaseClient
      .from('audiobooks')
      .insert({
        id: audioBookId,
        user_id: apiKeyData.user_id,
        title: metadata.title,
        duration_seconds: metadata.duration_seconds,
        storage_path: filePath,
        chapters_json: metadata.chapters_json || {}
      })

    if (dbError) {
      console.error('Database error:', dbError)
      // Try to clean up uploaded file
      await supabaseClient.storage
        .from('audiobooks')
        .remove([filePath])
      
      return new Response(
        JSON.stringify({ error: 'Failed to create audiobook record' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({ status: 'success', message: 'Audiobook created successfully.' }),
      { status: 201, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
