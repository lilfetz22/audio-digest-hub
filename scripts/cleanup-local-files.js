#!/usr/bin/env node

/**
 * Local Files Cleanup Scheduler
 * 
 * This script deletes old files from local audiobook processing folders.
 * Cleans up archive_mp3 and cleaned_full_texts directories.
 * 
 * Usage:
 *   node scripts/cleanup-local-files.js
 * 
 * Or add to your system cron (every Friday at 6 PM):
 *   0 18 * * 5 cd /path/to/audio-digest-hub && node scripts/cleanup-local-files.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get current file's directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const PROJECT_ROOT = path.join(__dirname, '..');
const FOLDERS_TO_CLEAN = [
  path.join(PROJECT_ROOT, 'src', 'audiobooks', 'archive_mp3'),
  path.join(PROJECT_ROOT, 'src', 'audiobooks', 'cleaned_full_texts')
];

/**
 * Delete files older than 7 days in a directory (but keep the directory itself)
 */
function cleanDirectory(dirPath) {
  if (!fs.existsSync(dirPath)) {
    console.log(`⚠️  Directory not found: ${dirPath}`);
    return { deleted: 0, errors: 0, kept: 0 };
  }

  let deleted = 0;
  let errors = 0;
  let kept = 0;
  const files = fs.readdirSync(dirPath);

  // Calculate the cutoff date (7 days ago from today)
  const today = new Date();
  today.setHours(0, 0, 0, 0); // Reset to start of day
  const cutoffDate = new Date(today);
  cutoffDate.setDate(cutoffDate.getDate() - 7);

  console.log(`📂 Cleaning: ${dirPath}`);
  console.log(`   Found ${files.length} items`);
  console.log(`   Cutoff date: ${cutoffDate.toLocaleDateString()} (files from this date or earlier will be deleted)`);

  files.forEach((file) => {
    const filePath = path.join(dirPath, file);
    const stats = fs.statSync(filePath);

    // Only process files, not subdirectories
    if (stats.isFile()) {
      try {
        // Get file's last modified date
        const fileDate = new Date(stats.mtime);
        fileDate.setHours(0, 0, 0, 0); // Reset to start of day for comparison

        // Delete if file is older than or equal to cutoff date
        if (fileDate <= cutoffDate) {
          fs.unlinkSync(filePath);
          console.log(`   ✅ Deleted: ${file} (last modified: ${stats.mtime.toLocaleDateString()})`);
          deleted++;
        } else {
          console.log(`   ⏭️  Kept: ${file} (last modified: ${stats.mtime.toLocaleDateString()})`);
          kept++;
        }
      } catch (error) {
        console.log(`   ❌ Failed to process ${file}: ${error.message}`);
        errors++;
      }
    } else if (stats.isDirectory()) {
      console.log(`   ⏭️  Skipped directory: ${file}`);
    }
  });

  return { deleted, errors, kept };
}

/**
 * Main cleanup function
 */
async function performCleanup() {
  const startTime = new Date();
  console.log(`🧹 Starting local files cleanup at ${startTime.toISOString()}`);
  console.log('');

  let totalDeleted = 0;
  let totalErrors = 0;

  let totalKept = 0;

  for (const folder of FOLDERS_TO_CLEAN) {
    const result = cleanDirectory(folder);
    totalDeleted += result.deleted;
    totalErrors += result.errors;
    totalKept += result.kept;
    console.log('');
  }

  const endTime = new Date();
  const duration = endTime - startTime;

  console.log('📊 Cleanup Summary:');
  console.log(`   ⏱️  Duration: ${duration}ms`);
  console.log(`   🗑️  Total files deleted: ${totalDeleted}`);
  console.log(`   📁 Total files kept: ${totalKept}`);
  if (totalErrors > 0) {
    console.log(`   ⚠️  Errors encountered: ${totalErrors}`);
  }

  return {
    success: true,
    deleted: totalDeleted,
    errors: totalErrors,
    duration
  };
}

/**
 * Check if this is the right day (Friday) when run automatically
 */
function shouldRunToday() {
  const today = new Date().getDay(); // 0 = Sunday, 5 = Friday
  return today === 5; // Only run on Friday
}

/**
 * Main execution
 */
async function main() {
  try {
    // Check if --force flag is provided to skip day check
    const force = process.argv.includes('--force');
    
    if (!force && !shouldRunToday()) {
      const today = new Date();
      console.log(`⏭️  Skipping cleanup - today is ${today.toLocaleDateString('en-US', { weekday: 'long' })}, not Friday`);
      console.log('   Use --force flag to run anyway');
      return;
    }
    
    const result = await performCleanup();
    
    if (result.errors > 0) {
      console.log('⚠️  Cleanup completed with errors');
      process.exit(1);
    } else {
      console.log('🎉 Cleanup process completed successfully!');
      process.exit(0);
    }
  } catch (error) {
    console.error('💥 Cleanup failed:', error.message);
    process.exit(1);
  }
}

// Run if this file is executed directly
main();

export { performCleanup };
