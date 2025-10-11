# Audiobook Cleanup Scripts

This directory contains scripts to automatically trigger the audiobook cleanup function every Friday.

## 🎯 What the Cleanup Does

The cleanup function deletes audiobooks that are older than a **Friday that's at least 7 days ago**. This ensures audiobooks get at least a full week to be enjoyed. For example:

- If run on Friday, October 11, 2025 → deletes audiobooks older than Friday, October 4, 2025 (7 days ago)
- If run on Saturday, October 12, 2025 → deletes audiobooks older than Friday, October 4, 2025 (8 days ago, not yesterday)
- If run on Monday, October 14, 2025 → deletes audiobooks older than Friday, October 4, 2025 (10 days ago)

**Key Rule**: Audiobooks always get at least 7 full days before being eligible for deletion.

## 📁 Available Scripts

### 1. `cleanup-trigger.js` (Node.js)
**Recommended for most users**

```bash
# Test the cleanup (runs regardless of day)
node scripts/cleanup-trigger.js --force

# Normal run (only runs on Friday)
node scripts/cleanup-trigger.js
```

### 2. `cleanup-trigger.ps1` (PowerShell)
**For Windows users with Task Scheduler**

```powershell
# Test the cleanup
.\scripts\cleanup-trigger.ps1 -Force

# Normal run
.\scripts\cleanup-trigger.ps1
```

### 3. `test-cleanup.bat` (Windows Batch)
**Quick test script**

Double-click to run a test cleanup immediately.

## 🕐 Setting Up Automatic Scheduling

### Option A: GitHub Actions (Recommended)
The `.github/workflows/cleanup.yml` file will automatically run every Friday at 6 PM UTC.

**Setup:**
1. Push your code to GitHub
2. Go to your repository settings
3. Add a repository secret named `SUPABASE_URL` with value: `https://fpflgstvoztlbmowvpeo.supabase.co`
4. The workflow will run automatically every Friday

### Option B: Windows Task Scheduler
**If you already have `run_audiobook_generator.bat` scheduled:**
The batch file has been updated to automatically run cleanup on Fridays. No additional setup needed!

**For standalone cleanup scheduling:**
1. Open Task Scheduler
2. Create Basic Task
3. Name: "Audiobook Cleanup"
4. Trigger: Weekly, on Fridays at 6:00 PM
5. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\your\audio-digest-hub\scripts\cleanup-trigger.ps1"`

### Option C: System Cron (Linux/Mac)
Add to your crontab:
```bash
# Run every Friday at 6:00 PM
0 18 * * 5 cd /path/to/audio-digest-hub && node scripts/cleanup-trigger.js
```

## 🧪 Testing

Before setting up automatic scheduling, test the cleanup function:

```bash
# Test with Node.js
node scripts/cleanup-trigger.js --force

# Test with PowerShell
.\scripts\cleanup-trigger.ps1 -Force

# Test with batch file (Windows)
.\scripts\test-cleanup.bat
```

## 🔍 Monitoring

The scripts provide detailed logging:
- ✅ Success messages show how many audiobooks were deleted
- 📋 Lists the titles and dates of deleted audiobooks  
- ⚠️ Warning messages for any errors
- 📊 Execution time and HTTP status

## 🛠️ Troubleshooting

### "Request failed" errors
- Check your internet connection
- Verify the Supabase URL is correct
- Check if the cleanup function is deployed

### "Skipping cleanup - not Friday"
- This is normal behavior for the automatic scheduling
- Use `--force` flag to test regardless of the day

### No audiobooks deleted
- This is normal if no audiobooks are older than the previous Friday
- Check the logs to see the cutoff date being used