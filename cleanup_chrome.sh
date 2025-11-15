#!/bin/bash
# Cleanup Chrome/Brave Processes Script
# Use this when Chrome/Brave launch fails

echo "🧹 Chrome/Brave Cleanup Script"
echo "=============================="
echo ""

# Kill zombie chromedrivers
echo "1️⃣  Killing zombie chromedrivers..."
pkill -9 -f "chromedriver.*defunct" 2>/dev/null && echo "   ✅ Killed zombie chromedrivers" || echo "   ℹ️  No zombie chromedrivers found"

# Kill all chromedrivers
echo "2️⃣  Killing all chromedrivers..."
pkill -9 chromedriver 2>/dev/null && echo "   ✅ Killed all chromedrivers" || echo "   ℹ️  No chromedrivers running"

# Kill all Chrome processes
echo "3️⃣  Killing all Chrome processes..."
CHROME_KILLED=0
pkill -9 chrome 2>/dev/null && CHROME_KILLED=1
pkill -9 google-chrome 2>/dev/null && CHROME_KILLED=1
pkill -9 chromium 2>/dev/null && CHROME_KILLED=1
pkill -9 chromium-browser 2>/dev/null && CHROME_KILLED=1

if [ "$CHROME_KILLED" -eq 1 ]; then
    echo "   ✅ Killed Chrome processes"
else
    echo "   ℹ️  No Chrome processes running"
fi

# Kill all Brave processes
echo "4️⃣  Killing all Brave browser processes..."
BRAVE_KILLED=0
pkill -9 brave 2>/dev/null && BRAVE_KILLED=1
pkill -9 brave-browser 2>/dev/null && BRAVE_KILLED=1
pkill -9 BraveBrowser 2>/dev/null && BRAVE_KILLED=1

if [ "$BRAVE_KILLED" -eq 1 ]; then
    echo "   ✅ Killed Brave browser processes"
else
    echo "   ℹ️  No Brave processes running"
fi

# Remove profile locks
echo "5️⃣  Removing profile locks..."
PROFILE_DIR="$HOME/Documents/Projects/aistudio-generate-speech/desktop_audio_generator/chrome_profiles"
if [ -d "$PROFILE_DIR" ]; then
    LOCK_COUNT=$(find "$PROFILE_DIR" -name "Singleton*" 2>/dev/null | wc -l)
    if [ "$LOCK_COUNT" -gt 0 ]; then
        find "$PROFILE_DIR" -name "SingletonLock" -delete 2>/dev/null
        find "$PROFILE_DIR" -name "SingletonSocket" -delete 2>/dev/null
        find "$PROFILE_DIR" -name "SingletonCookie" -delete 2>/dev/null
        echo "   ✅ Removed $LOCK_COUNT lock files"
    else
        echo "   ℹ️  No lock files found"
    fi
else
    echo "   ⚠️  Profile directory not found"
fi

# Wait for cleanup
echo "6️⃣  Waiting for cleanup..."
sleep 2
echo "   ✅ Done"

echo ""
echo "✨ Cleanup complete!"
echo "🚀 You can now launch Chrome/Brave."
echo ""
