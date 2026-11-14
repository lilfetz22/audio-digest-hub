import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// Pasted-text TTS jobs. The browser creates and polls jobs with its Supabase
// JWT. The GitHub Actions runner (src/audiobooks/tts_on_demand.py) reads the
// text and reports progress with the pipeline's API key.
//
// Routes:
//   POST   /tts-jobs              (JWT)      create job, dispatch the workflow
//   GET    /tts-jobs              (JWT)      recent jobs for the user
//   GET    /tts-jobs/:id          (JWT)      one job (the page polls this)
//   GET    /tts-jobs/:id/input    (API key)  text + title for the runner
//   PATCH  /tts-jobs/:id          (API key)  runner progress / final status

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
}

const INPUT_BUCKET = 'tts-input'
const WORKFLOW_FILE = 'tts-on-demand.yml'
const MAX_TEXT_CHARS = 200_000
const MAX_TITLE_CHARS = 200
const RECENT_JOB_LIMIT = 20
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const STATUSES = ['queued', 'starting', 'synthesizing', 'uploading', 'done', 'failed'] as const
const TERMINAL_STATUSES = ['done', 'failed']

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  })
}

// Returns the authenticated user id and how they authenticated, or null.
async function authenticate(
  supabase: ReturnType<typeof createClient>,
  token: string,
): Promise<{ userId: string; via: 'jwt' | 'apikey' } | null> {
  const { data: { user: jwtUser } } = await supabase.auth.getUser(token)
  if (jwtUser) {
    return { userId: jwtUser.id, via: 'jwt' }
  }

  const hashBuffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))
  const keyHash = Array.from(new Uint8Array(hashBuffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')

  const { data: apiKeyData, error } = await supabase
    .from('api_keys')
    .select('user_id')
    .eq('key_hash', keyHash)
    .single()

  if (error || !apiKeyData) {
    return null
  }

  await supabase
    .from('api_keys')
    .update({ last_used_at: new Date().toISOString() })
    .eq('key_hash', keyHash)

  return { userId: apiKeyData.user_id, via: 'apikey' }
}

// Start the GitHub Actions run that synthesizes this job.
async function dispatchWorkflow(jobId: string): Promise<void> {
  const repo = Deno.env.get('GITHUB_REPO') ?? ''
  const token = Deno.env.get('GITHUB_DISPATCH_TOKEN') ?? ''
  const ref = Deno.env.get('GITHUB_REF') ?? 'main'
  if (!repo || !token) {
    throw new Error('GITHUB_REPO or GITHUB_DISPATCH_TOKEN is not configured')
  }

  const response = await fetch(
    `https://api.github.com/repos/${repo}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ref, inputs: { job_id: jobId } }),
    },
  )
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`GitHub dispatch failed (${response.status}): ${detail}`)
  }
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    )

    const authHeader = req.headers.get('Authorization')
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return json({ error: 'Missing or invalid authorization header' }, 401)
    }

    const auth = await authenticate(supabase, authHeader.substring(7))
    if (!auth) {
      return json({ error: 'Invalid credentials' }, 401)
    }
    const { userId, via } = auth

    // Route: everything after the "tts-jobs" path segment.
    const segments = new URL(req.url).pathname.split('/').filter(Boolean)
    const rest = segments.slice(segments.indexOf('tts-jobs') + 1)
    const jobId = rest[0]
    const isInput = rest[1] === 'input' && rest.length === 2

    if (jobId !== undefined && !UUID_PATTERN.test(jobId)) {
      return json({ error: 'Invalid job id' }, 400)
    }

    // Loads a job and enforces ownership. Returns null if missing or not theirs.
    const loadOwnedJob = async (id: string) => {
      const { data, error } = await supabase
        .from('tts_jobs')
        .select('*')
        .eq('id', id)
        .eq('user_id', userId)
        .single()
      return error || !data ? null : data
    }

    // POST /tts-jobs — browser submits pasted text
    if (req.method === 'POST' && jobId === undefined) {
      if (via !== 'jwt') {
        return json({ error: 'Job creation requires a signed-in user' }, 403)
      }

      const body = await req.json().catch(() => null)
      const text = typeof body?.text === 'string' ? body.text : ''
      const title = typeof body?.title === 'string' ? body.title.trim().slice(0, MAX_TITLE_CHARS) : ''

      if (!text.trim()) {
        return json({ error: 'Text is required' }, 400)
      }
      if (text.length > MAX_TEXT_CHARS) {
        return json({ error: `Text is too long (max ${MAX_TEXT_CHARS} characters)` }, 413)
      }

      const newJobId = crypto.randomUUID()
      const { error: uploadError } = await supabase.storage
        .from(INPUT_BUCKET)
        .upload(`${userId}/${newJobId}.txt`, new Blob([text], { type: 'text/plain' }), {
          contentType: 'text/plain',
          upsert: false,
        })
      if (uploadError) {
        console.error('Input upload error:', uploadError)
        return json({ error: 'Failed to store text' }, 500)
      }

      const { error: insertError } = await supabase.from('tts_jobs').insert({
        id: newJobId,
        user_id: userId,
        title: title || null,
        status: 'queued',
        percent: 0,
      })
      if (insertError) {
        console.error('Job insert error:', insertError)
        return json({ error: 'Failed to create job' }, 500)
      }

      try {
        await dispatchWorkflow(newJobId)
      } catch (err) {
        console.error('Dispatch error:', err)
        await supabase
          .from('tts_jobs')
          .update({ status: 'failed', error: 'Could not start the audio worker' })
          .eq('id', newJobId)
        return json({ error: 'Could not start the audio worker' }, 502)
      }

      return json({ id: newJobId, status: 'queued' }, 201)
    }

    // GET /tts-jobs — recent jobs for the signed-in user
    if (req.method === 'GET' && jobId === undefined) {
      const { data, error } = await supabase
        .from('tts_jobs')
        .select('id, title, status, percent, error, created_at, updated_at')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(RECENT_JOB_LIMIT)
      if (error) {
        return json({ error: 'Failed to load jobs' }, 500)
      }
      return json(data)
    }

    // GET /tts-jobs/:id/input — runner fetches the text
    if (req.method === 'GET' && isInput) {
      if (via !== 'apikey') {
        return json({ error: 'Input is only available to the worker' }, 403)
      }
      const job = await loadOwnedJob(jobId!)
      if (!job) {
        return json({ error: 'Job not found' }, 404)
      }

      const { data: file, error: downloadError } = await supabase.storage
        .from(INPUT_BUCKET)
        .download(`${userId}/${jobId}.txt`)
      if (downloadError || !file) {
        console.error('Input download error:', downloadError)
        return json({ error: 'Job text not found' }, 404)
      }

      return json({ title: job.title, text: await file.text() })
    }

    // GET /tts-jobs/:id — page polls progress
    if (req.method === 'GET' && jobId !== undefined && rest.length === 1) {
      const job = await loadOwnedJob(jobId)
      if (!job) {
        return json({ error: 'Job not found' }, 404)
      }
      return json({
        id: job.id,
        title: job.title,
        status: job.status,
        percent: job.percent,
        error: job.error,
        created_at: job.created_at,
        updated_at: job.updated_at,
      })
    }

    // PATCH /tts-jobs/:id — runner reports progress and final status
    if (req.method === 'PATCH' && jobId !== undefined && rest.length === 1) {
      if (via !== 'apikey') {
        return json({ error: 'Progress updates are only accepted from the worker' }, 403)
      }

      const body = await req.json().catch(() => null)
      const update: Record<string, unknown> = {}

      if (body?.status !== undefined) {
        if (!STATUSES.includes(body.status)) {
          return json({ error: 'Invalid status' }, 400)
        }
        update.status = body.status
      }
      if (body?.percent !== undefined) {
        if (!Number.isInteger(body.percent) || body.percent < 0 || body.percent > 100) {
          return json({ error: 'percent must be an integer from 0 to 100' }, 400)
        }
        update.percent = body.percent
      }
      if (body?.error !== undefined) {
        update.error = typeof body.error === 'string' ? body.error.slice(0, 500) : null
      }
      if (Object.keys(update).length === 0) {
        return json({ error: 'Nothing to update' }, 400)
      }

      const job = await loadOwnedJob(jobId)
      if (!job) {
        return json({ error: 'Job not found' }, 404)
      }
      // A finished job is final. Ignore late progress from a retried run.
      if (TERMINAL_STATUSES.includes(job.status)) {
        return json({ error: 'Job already finished' }, 409)
      }

      if (update.status === 'done') {
        update.percent = 100
      }

      const { data, error } = await supabase
        .from('tts_jobs')
        .update({ ...update, updated_at: new Date().toISOString() })
        .eq('id', jobId)
        .eq('user_id', userId)
        .select('id, status, percent')
        .single()
      if (error) {
        console.error('Job update error:', error)
        return json({ error: 'Failed to update job' }, 500)
      }

      // The input text is no longer needed once the audio is done.
      if (update.status === 'done') {
        await supabase.storage.from(INPUT_BUCKET).remove([`${userId}/${jobId}.txt`])
      }

      return json(data)
    }

    return json({ error: 'Not found' }, 404)
  } catch (err) {
    console.error('Unhandled error:', err)
    return json({ error: 'Internal server error' }, 500)
  }
})
