@echo off
echo Testing audiobook cleanup function...
echo.

cd /d "%~dp0.."

:: Test the cleanup function immediately (force run)
node scripts\cleanup-trigger.js --force

echo.
echo Test completed. Press any key to exit...
pause > nul