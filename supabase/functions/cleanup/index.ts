
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const RESEARCH_PAPER_DATE_PATTERN = /^(\d{4}-\d{2}-\d{2})\.json$/

serve(async (req) => {
  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Calculate the cutoff Friday (at least 7 days ago)
    // This ensures all audiobooks get at least a full week to be enjoyed
    const now = new Date()
    const currentDay = now.getDay() // 0 = Sunday, 1 = Monday, ..., 5 = Friday, 6 = Saturday

    // Calculate days to subtract to get to a Friday that's at least 7 days ago
    let daysToSubtract
    if (currentDay === 5) { // If today is Friday
      daysToSubtract = 7 // Get last Friday (a week ago)
    } else if (currentDay === 6) { // If today is Saturday
      daysToSubtract = 8 // Get Friday from a week ago (not yesterday)
    } else { // Sunday (0) through Thursday (4)
      // For Sunday through Thursday, go back to the Friday before last
      daysToSubtract = currentDay + 9 // Sunday=9, Monday=10, Tuesday=11, Wednesday=12, Thursday=13
    }

    const cutoffFriday = new Date(now)
    cutoffFriday.setDate(now.getDate() - daysToSubtract)
    cutoffFriday.setHours(23, 59, 59, 999) // End of that Friday

    console.log(`Current date: ${now.toISOString()}`)
    console.log(`Deleting audiobooks older than: ${cutoffFriday.toISOString()}`)

    // Find audiobooks older than the cutoff Friday
    const { data: oldAudiobooks, error: fetchError } = await supabaseClient
      .from('audiobooks')
      .select('id, storage_path, created_at, title')
      .lt('created_at', cutoffFriday.toISOString())

    if (fetchError) {
      throw fetchError
    }

    let cleanedCount = 0
    let cleanedResearchPaperCount = 0
    const errors = []
    const deletedAudiobooks = []

    console.log(`Found ${oldAudiobooks?.length ?? 0} audiobooks to delete`)

    // Delete each old audiobook
    for (const audiobook of oldAudiobooks ?? []) {
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

    const paperCutoff = new Date(now)
    paperCutoff.setDate(now.getDate() - 30)
    paperCutoff.setHours(0, 0, 0, 0)
    console.log(`Deleting research-paper metadata older than: ${paperCutoff.toISOString()}`)

    const { data: userFolders, error: folderError } = await supabaseClient.storage
      .from('research-papers')
      .list('', { limit: 1000 })

    if (folderError) {
      errors.push(`Failed to list research-paper user folders: ${folderError.message}`)
    } else {
      for (const userFolder of userFolders ?? []) {
        let offset = 0
        const pageSize = 1000

        while (true) {
          const { data: paperFiles, error: listError } = await supabaseClient.storage
            .from('research-papers')
            .list(userFolder.name, { limit: pageSize, offset })

          if (listError) {
            errors.push(`Failed to list research papers for ${userFolder.name}: ${listError.message}`)
            break
          }

          for (const paperFile of paperFiles ?? []) {
            const match = paperFile.name.match(RESEARCH_PAPER_DATE_PATTERN)
            if (!match) continue

            const fileDate = new Date(`${match[1]}T00:00:00.000Z`)
            if (fileDate >= paperCutoff) continue

            const filePath = `${userFolder.name}/${paperFile.name}`
            const { error: removeError } = await supabaseClient.storage
              .from('research-papers')
              .remove([filePath])

            if (removeError) {
              console.error(`Failed to delete ${filePath}:`, removeError)
              errors.push(`Research-paper deletion failed for ${filePath}`)
              continue
            }

            cleanedResearchPaperCount++
            console.log(`Deleted research-paper metadata: ${filePath}`)
          }

          if (!paperFiles || paperFiles.length < pageSize) break
          offset += pageSize
        }
      }
    }

    return new Response(
      JSON.stringify({
        message: `Cleanup completed. ${cleanedCount} audiobooks and ${cleanedResearchPaperCount} research-paper files removed.`,
        cleaned: cleanedCount,
        cleanedResearchPapers: cleanedResearchPaperCount,
        cutoffDate: cutoffFriday.toISOString(),
        researchPaperCutoffDate: paperCutoff.toISOString(),
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
