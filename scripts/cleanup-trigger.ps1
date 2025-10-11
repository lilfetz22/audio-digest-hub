# Audiobook Cleanup Trigger for Windows Task Scheduler
# 
# To set up with Windows Task Scheduler:
# 1. Open Task Scheduler
# 2. Create Basic Task
# 3. Set trigger to Weekly, on Fridays
# 4. Set action to "Start a program"
# 5. Program: powershell.exe
# 6. Arguments: -ExecutionPolicy Bypass -File "C:\path\to\your\scripts\cleanup-trigger.ps1"

param(
    [switch]$Force = $false
)

# Configuration
$SUPABASE_URL = $env:SUPABASE_URL
if (-not $SUPABASE_URL) {
    $SUPABASE_URL = "https://fpflgstvoztlbmowvpeo.supabase.co"
}

$CLEANUP_ENDPOINT = "$SUPABASE_URL/functions/v1/cleanup"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

function Test-ShouldRunToday {
    $today = (Get-Date).DayOfWeek
    return $today -eq 'Friday'
}

function Invoke-CleanupFunction {
    try {
        Write-Log "🧹 Starting audiobook cleanup..." "INFO"
        
        $startTime = Get-Date
        
        $response = Invoke-RestMethod -Uri $CLEANUP_ENDPOINT -Method POST -ContentType "application/json" -TimeoutSec 30
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds
        
        Write-Log "📊 Cleanup completed in $($duration)ms" "INFO"
        Write-Log "✅ Success: $($response.message)" "SUCCESS"
        
        if ($response.cleaned -gt 0) {
            Write-Log "🗑️ Deleted $($response.cleaned) audiobooks" "INFO"
            
            if ($response.deletedAudiobooks) {
                $response.deletedAudiobooks | ForEach-Object -Begin { $i = 1 } -Process {
                    Write-Log "   $i. $($_.title) ($($_.created_at))" "INFO"
                    $i++
                }
            }
        }
        
        if ($response.errors) {
            Write-Log "⚠️ Some errors occurred:" "WARNING"
            $response.errors | ForEach-Object {
                Write-Log "   - $_" "WARNING"
            }
        }
        
        return $response
        
    } catch {
        Write-Log "❌ Cleanup failed: $($_.Exception.Message)" "ERROR"
        throw
    }
}

# Main execution
try {
    if (-not $Force -and -not (Test-ShouldRunToday)) {
        $today = (Get-Date).DayOfWeek
        Write-Log "⏭️ Skipping cleanup - today is $today, not Friday" "INFO"
        Write-Log "   Use -Force parameter to run anyway" "INFO"
        exit 0
    }
    
    $result = Invoke-CleanupFunction
    Write-Log "🎉 Cleanup process completed successfully!" "SUCCESS"
    exit 0
    
} catch {
    Write-Log "💥 Cleanup process failed: $($_.Exception.Message)" "ERROR"
    exit 1
}