
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Calculate date 30 days ago
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

    // Find audiobooks older than 30 days
    const { data: oldAudiobooks, error: fetchError } = await supabaseClient
      .from('audiobooks')
      .select('id, storage_path')
      .lt('created_at', thirtyDaysAgo.toISOString())

    if (fetchError) {
      throw fetchError
    }

    if (!oldAudiobooks || oldAudiobooks.length === 0) {
      return new Response(
        JSON.stringify({ message: 'No audiobooks to cleanup', cleaned: 0 }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    }

    let cleanedCount = 0
    const errors = []

    // Delete each old audiobook
    for (const audiobook of oldAudiobooks) {
      try {
        // Delete from storage
        const { error: storageError } = await supabaseClient.storage
          .from('audiobooks')
          .remove([audiobook.storage_path])

        if (storageError) {
          console.error(`Failed to delete ${audiobook.storage_path}:`, storageError)
          errors.push(`Storage deletion failed for ${audiobook.id}`)
          continue
        }

        // Delete from database
        const { error: dbError } = await supabaseClient
          .from('audiobooks')
          .delete()
          .eq('id', audiobook.id)

        if (dbError) {
          console.error(`Failed to delete audiobook ${audiobook.id}:`, dbError)
          errors.push(`Database deletion failed for ${audiobook.id}`)
          continue
        }

        cleanedCount++
      } catch (error) {
        console.error(`Error cleaning up audiobook ${audiobook.id}:`, error)
        errors.push(`General error for ${audiobook.id}`)
      }
    }

    return new Response(
      JSON.stringify({ 
        message: `Cleanup completed. ${cleanedCount} audiobooks removed.`,
        cleaned: cleanedCount,
        errors: errors.length > 0 ? errors : undefined
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Cleanup function error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error during cleanup' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})
