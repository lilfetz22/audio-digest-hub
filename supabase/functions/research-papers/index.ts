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

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Authenticate via API key (same pattern as other edge functions)
    const authHeader = req.headers.get('Authorization')
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(
        JSON.stringify({ error: 'Missing or invalid authorization header' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const apiKey = authHeader.substring(7)
    const encoder = new TextEncoder()
    const data = encoder.encode(apiKey)
    const hashBuffer = await crypto.subtle.digest('SHA-256', data)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    const keyHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')

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

    await supabaseClient
      .from('api_keys')
      .update({ last_used_at: new Date().toISOString() })
      .eq('key_hash', keyHash)

    const userId = apiKeyData.user_id
    const url = new URL(req.url)

    // POST: Pipeline pushes daily paper list
    if (req.method === 'POST') {
      const body = await req.json()
      const { date, papers } = body

      if (!date || !papers || !Array.isArray(papers)) {
        return new Response(
          JSON.stringify({ error: 'Missing date or papers array' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      const filePath = `${userId}/${date}.json`
      const fileContent = JSON.stringify({ date, papers })

      const { error: uploadError } = await supabaseClient.storage
        .from('research-papers')
        .upload(filePath, fileContent, {
          contentType: 'application/json',
          upsert: true,
        })

      if (uploadError) {
        console.error('Upload error:', uploadError)
        return new Response(
          JSON.stringify({ error: 'Failed to store paper data' }),
          { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      return new Response(
        JSON.stringify({ status: 'success', message: `Stored ${papers.length} papers for ${date}` }),
        { status: 201, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // GET: Fetch papers for a date, or feedback data
    if (req.method === 'GET') {
      const feedbackMode = url.searchParams.get('feedback')
      const days = parseInt(url.searchParams.get('days') || '30', 10)

      if (feedbackMode === 'true') {
        // Feedback mode: return all clicked papers from the last N days
        const allData = []
        const today = new Date()

        for (let i = 0; i < days; i++) {
          const d = new Date(today)
          d.setDate(today.getDate() - i)
          const dateStr = d.toISOString().split('T')[0]
          const filePath = `${userId}/${dateStr}.json`

          const { data: fileData, error: downloadError } = await supabaseClient.storage
            .from('research-papers')
            .download(filePath)

          if (!downloadError && fileData) {
            try {
              const text = await fileData.text()
              const parsed = JSON.parse(text)
              allData.push(parsed)
            } catch {
              // Skip malformed files
            }
          }
        }

        return new Response(
          JSON.stringify(allData),
          { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      // Regular mode: fetch papers for a specific date
      const date = url.searchParams.get('date')
      if (!date) {
        return new Response(
          JSON.stringify({ error: 'Missing date parameter' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      const filePath = `${userId}/${date}.json`
      const { data: fileData, error: downloadError } = await supabaseClient.storage
        .from('research-papers')
        .download(filePath)

      if (downloadError) {
        return new Response(
          JSON.stringify({ date, papers: [] }),
          { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      const text = await fileData.text()
      const parsed = JSON.parse(text)

      return new Response(
        JSON.stringify(parsed),
        { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // PATCH: Mark a paper as clicked
    if (req.method === 'PATCH') {
      const body = await req.json()
      const { date, paper_url } = body

      if (!date || !paper_url) {
        return new Response(
          JSON.stringify({ error: 'Missing date or paper_url' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      const filePath = `${userId}/${date}.json`

      // Download existing data
      const { data: fileData, error: downloadError } = await supabaseClient.storage
        .from('research-papers')
        .download(filePath)

      if (downloadError || !fileData) {
        return new Response(
          JSON.stringify({ error: 'Paper data not found for this date' }),
          { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      const text = await fileData.text()
      const parsed = JSON.parse(text)

      // Mark the paper as clicked
      let found = false
      for (const paper of parsed.papers) {
        if (paper.url === paper_url) {
          paper.clicked = true
          found = true
          break
        }
      }

      if (!found) {
        return new Response(
          JSON.stringify({ error: 'Paper URL not found' }),
          { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      // Re-upload the updated data
      const updatedContent = JSON.stringify(parsed)
      const { error: uploadError } = await supabaseClient.storage
        .from('research-papers')
        .upload(filePath, updatedContent, {
          contentType: 'application/json',
          upsert: true,
        })

      if (uploadError) {
        return new Response(
          JSON.stringify({ error: 'Failed to update paper data' }),
          { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      return new Response(
        JSON.stringify({ status: 'success', message: 'Paper marked as clicked' }),
        { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})
