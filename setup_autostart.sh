#!/bin/bash
# Run this once on your Mac to install the email agent as a background service.
# It will start automatically when you log in and restart if it ever crashes.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.usgovtservices.emailagent"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
LOG_PATH="$HOME/Library/Logs/email-agent.log"
PYTHON="$(which python3)"

echo "Setting up Email Agent as a Mac background service..."
echo ""
echo "Project folder: $SCRIPT_DIR"
echo "Python:         $PYTHON"
echo "Log file:       $LOG_PATH"
echo ""

# Create the LaunchAgents folder if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$HOME/Library/Logs"

# Write the plist file
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$SCRIPT_DIR/agent.py</string>
        <string>--watch</string>
        <string>--interval</string>
        <string>15</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <!-- Start automatically when you log in -->
    <key>RunAtLoad</key>
    <true/>

    <!-- Restart automatically if it crashes -->
    <key>KeepAlive</key>
    <true/>

    <!-- Save all output to a log file -->
    <key>StandardOutPath</key>
    <string>$LOG_PATH</string>
    <key>StandardErrorPath</key>
    <string>$LOG_PATH</string>

    <!-- Wait 30 seconds before restarting after a crash -->
    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
EOF

# Load it now (no need to restart)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✅ Done! The email agent is now running in the background."
echo ""
echo "Useful commands:"
echo "  Check if it's running:  launchctl list | grep emailagent"
echo "  View live logs:         tail -f ~/Library/Logs/email-agent.log"
echo "  Stop the agent:         launchctl unload ~/Library/LaunchAgents/$PLIST_NAME.plist"
echo "  Start it again:         launchctl load ~/Library/LaunchAgents/$PLIST_NAME.plist"
echo "  Uninstall completely:   bash $SCRIPT_DIR/uninstall_autostart.sh"
