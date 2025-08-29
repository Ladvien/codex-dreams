#!/bin/bash
# macOS launchd service installation script for Codex Dreams Daemon

set -e

# Configuration
SERVICE_NAME="com.codex-dreams.daemon"
PLIST_NAME="${SERVICE_NAME}.plist"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
USER_MODE=false
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --user)
            USER_MODE=true
            shift
            ;;
        --system)
            USER_MODE=false
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--user|--system] [--force]"
            echo "  --user    Install as user service (default: system service)"
            echo "  --system  Install as system service"
            echo "  --force   Overwrite existing service"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Installing Codex Dreams Daemon for macOS..."
echo "Project Directory: $PROJECT_DIR"
echo "Service Name: $SERVICE_NAME"
echo "User Mode: $USER_MODE"

# Determine installation paths
if [ "$USER_MODE" = true ]; then
    PLIST_DIR="$HOME/Library/LaunchAgents"
    LOG_DIR="$HOME/Library/Logs/codex-dreams"
    LAUNCHCTL_DOMAIN="gui/$(id -u)"
else
    PLIST_DIR="/Library/LaunchDaemons"
    LOG_DIR="/var/log/codex-dreams"
    LAUNCHCTL_DOMAIN="system"
    
    # Check for admin privileges
    if [ "$EUID" -ne 0 ]; then
        echo "Error: System service installation requires sudo privileges"
        exit 1
    fi
fi

PLIST_PATH="$PLIST_DIR/$PLIST_NAME"

# Create directories
mkdir -p "$PLIST_DIR"
mkdir -p "$LOG_DIR"

# Find Python executable
PYTHON_EXE=""
for candidate in "$PROJECT_DIR/venv/bin/python3" "/usr/local/bin/python3" "/usr/bin/python3" "python3"; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON_EXE="$candidate"
        break
    fi
done

if [ -z "$PYTHON_EXE" ]; then
    echo "Error: Could not find Python 3 executable"
    exit 1
fi

echo "Using Python: $PYTHON_EXE"

# Check if service already exists
if [ -f "$PLIST_PATH" ] && [ "$FORCE" != true ]; then
    echo "Error: Service already exists at $PLIST_PATH"
    echo "Use --force to overwrite, or uninstall first with:"
    echo "  launchctl bootout $LAUNCHCTL_DOMAIN/$SERVICE_NAME"
    exit 1
fi

# Stop and unload existing service if it exists
if launchctl print "$LAUNCHCTL_DOMAIN/$SERVICE_NAME" >/dev/null 2>&1; then
    echo "Stopping existing service..."
    launchctl bootout "$LAUNCHCTL_DOMAIN/$SERVICE_NAME" 2>/dev/null || true
fi

# Create plist file
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$SERVICE_NAME</string>
    
    <key>Program</key>
    <string>$PYTHON_EXE</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_EXE</string>
        <string>-m</string>
        <string>src.daemon.scheduler</string>
        <string>--daemon</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    
    <key>ProcessType</key>
    <string>Background</string>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/daemon.log</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/daemon.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>$PROJECT_DIR</string>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF

# Set appropriate permissions
if [ "$USER_MODE" = true ]; then
    chmod 644 "$PLIST_PATH"
else
    chown root:wheel "$PLIST_PATH"
    chmod 644 "$PLIST_PATH"
fi

# Load the service
echo "Loading service..."
launchctl bootstrap "$LAUNCHCTL_DOMAIN" "$PLIST_PATH"

# Enable the service (start at boot)
launchctl enable "$LAUNCHCTL_DOMAIN/$SERVICE_NAME"

echo ""
echo "✅ Successfully installed Codex Dreams Daemon service!"
echo ""
echo "Service Details:"
echo "  Name: $SERVICE_NAME"
echo "  Plist: $PLIST_PATH"
echo "  Logs: $LOG_DIR/daemon.log"
echo ""
echo "Management Commands:"
echo "  Start:   launchctl kickstart $LAUNCHCTL_DOMAIN/$SERVICE_NAME"
echo "  Stop:    launchctl kill TERM $LAUNCHCTL_DOMAIN/$SERVICE_NAME"
echo "  Status:  launchctl print $LAUNCHCTL_DOMAIN/$SERVICE_NAME"
echo "  Unload:  launchctl bootout $LAUNCHCTL_DOMAIN/$SERVICE_NAME"
echo ""
echo "The service will start automatically at boot and restart if it crashes."