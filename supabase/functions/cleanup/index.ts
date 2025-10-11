
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Calculate the previous Friday
    const now = new Date()
    const currentDay = now.getDay() // 0 = Sunday, 1 = Monday, ..., 5 = Friday, 6 = Saturday
    
    // Calculate days to subtract to get to the previous Friday
    let daysToSubtract
    if (currentDay === 5) { // If today is Friday
      daysToSubtract = 7 // Get last Friday (a week ago)
    } else if (currentDay === 6) { // If today is Saturday
      daysToSubtract = 1 // Get yesterday (Friday)
    } else { // Sunday (0) through Thursday (4)
      daysToSubtract = currentDay + 2 // Sunday=2, Monday=3, Tuesday=4, Wednesday=5, Thursday=6
    }
    
    const previousFriday = new Date(now)
    previousFriday.setDate(now.getDate() - daysToSubtract)
    previousFriday.setHours(23, 59, 59, 999) // End of that Friday
    
    console.log(`Current date: ${now.toISOString()}`)
    console.log(`Deleting audiobooks older than: ${previousFriday.toISOString()}`)

    // Find audiobooks older than the previous Friday
    const { data: oldAudiobooks, error: fetchError } = await supabaseClient
      .from('audiobooks')
      .select('id, storage_path, created_at, title')
      .lt('created_at', previousFriday.toISOString())

    if (fetchError) {
      throw fetchError
    }

    if (!oldAudiobooks || oldAudiobooks.length === 0) {
      return new Response(
        JSON.stringify({ 
          message: `No audiobooks to cleanup (checked for audiobooks older than ${previousFriday.toISOString()})`, 
          cleaned: 0,
          cutoffDate: previousFriday.toISOString()
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    }

    let cleanedCount = 0
    const errors = []
    const deletedAudiobooks = []

    console.log(`Found ${oldAudiobooks.length} audiobooks to delete`)

    // Delete each old audiobook
    for (const audiobook of oldAudiobooks) {
      try {
        console.log(`Deleting audiobook: ${audiobook.title} (${audiobook.created_at})`)
        
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
        deletedAudiobooks.push({
          id: audiobook.id,
          title: audiobook.title,
          created_at: audiobook.created_at
        })
      } catch (error) {
        console.error(`Error cleaning up audiobook ${audiobook.id}:`, error)
        errors.push(`General error for ${audiobook.id}: ${audiobook.title}`)
      }
    }

    return new Response(
      JSON.stringify({ 
        message: `Cleanup completed. ${cleanedCount} audiobooks removed.`,
        cleaned: cleanedCount,
        cutoffDate: previousFriday.toISOString(),
        deletedAudiobooks: deletedAudiobooks,
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
