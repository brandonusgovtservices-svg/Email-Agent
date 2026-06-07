#!/bin/bash
# Removes the email agent background service from your Mac.

PLIST_NAME="com.usgovtservices.emailagent"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm "$PLIST_PATH"
    echo "✅ Email agent background service removed."
    echo "   Your project files and credentials are untouched."
else
    echo "No background service found — nothing to remove."
fi
