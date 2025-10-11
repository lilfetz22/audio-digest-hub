#!/usr/bin/env node

/**
 * Audiobook Cleanup Scheduler
 * 
 * This script can be used to trigger the cleanup function.
 * You can run this manually or set it up with your system's cron.
 * 
 * Usage:
 *   node scripts/cleanup-trigger.js
 * 
 * Or add to your system cron (every Friday at 6 PM):
 *   0 18 * * 5 cd /path/to/audio-digest-hub && node scripts/cleanup-trigger.js
 */

import https from 'https';
import { URL } from 'url';

// Configuration - you can also use environment variables
const SUPABASE_URL = process.env.SUPABASE_URL || 'https://fpflgstvoztlbmowvpeo.supabase.co';
const CLEANUP_ENDPOINT = `${SUPABASE_URL}/functions/v1/cleanup`;

async function triggerCleanup() {
  const startTime = new Date();
  console.log(`🧹 Starting cleanup at ${startTime.toISOString()}`);
  
  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(CLEANUP_ENDPOINT);
    
    const options = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || 443,
      path: parsedUrl.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'AudioDigestHub-CleanupScheduler/1.0'
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        const endTime = new Date();
        const duration = endTime - startTime;
        
        console.log(`📊 Cleanup completed in ${duration}ms`);
        console.log(`📈 HTTP Status: ${res.statusCode}`);
        
        try {
          const responseData = JSON.parse(data);
          console.log('📋 Response:', JSON.stringify(responseData, null, 2));
          
          if (res.statusCode === 200) {
            console.log(`✅ Success: ${responseData.message}`);
            if (responseData.cleaned > 0) {
              console.log(`🗑️  Deleted ${responseData.cleaned} audiobooks`);
              if (responseData.deletedAudiobooks) {
                responseData.deletedAudiobooks.forEach((audiobook, index) => {
                  console.log(`   ${index + 1}. ${audiobook.title} (${audiobook.created_at})`);
                });
              }
            }
            resolve(responseData);
          } else {
            console.log(`❌ Error: ${responseData.error || 'Unknown error'}`);
            reject(new Error(`HTTP ${res.statusCode}: ${responseData.error || data}`));
          }
        } catch (parseError) {
          console.log('❌ Failed to parse response:', data);
          reject(new Error(`Parse error: ${parseError.message}`));
        }
      });
    });

    req.on('error', (error) => {
      console.log(`❌ Request failed:`, error.message);
      reject(error);
    });

    req.setTimeout(30000, () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });

    req.end();
  });
}

// Check if this is the right day (Friday) when run automatically
function shouldRunToday() {
  const today = new Date().getDay(); // 0 = Sunday, 5 = Friday
  return today === 5; // Only run on Friday
}

// Main execution
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
    
    await triggerCleanup();
    console.log('🎉 Cleanup process completed successfully!');
    process.exit(0);
  } catch (error) {
    console.error('💥 Cleanup failed:', error.message);
    process.exit(1);
  }
}

// Run if this file is executed directly
main();

export { triggerCleanup };