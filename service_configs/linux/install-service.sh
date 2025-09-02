#!/bin/bash
# Linux systemd service installation script for Codex Dreams Daemon

set -e

# Configuration
SERVICE_NAME="codex-dreams-daemon"
SERVICE_FILE="${SERVICE_NAME}.service"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
USER_MODE=false
FORCE=false
SERVICE_USER="codex-dreams"
INSTALL_DIR="/opt/codex-dreams"

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
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --service-user)
            SERVICE_USER="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --user              Install as user service"
            echo "  --system            Install as system service (default)"
            echo "  --force             Overwrite existing service"
            echo "  --install-dir DIR   Installation directory (default: /opt/codex-dreams)"
            echo "  --service-user USER Service user (default: codex-dreams)"
            echo "  -h, --help          Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Installing Codex Dreams Daemon for Linux systemd..."
echo "Project Directory: $PROJECT_DIR"
echo "Service Name: $SERVICE_NAME"
echo "User Mode: $USER_MODE"

# Determine installation paths
if [ "$USER_MODE" = true ]; then
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    LOG_DIR="$HOME/.local/share/codex-dreams/logs"
    DATA_DIR="$HOME/.local/share/codex-dreams/data"
    INSTALL_DIR="$PROJECT_DIR"  # Use current directory for user mode
    SERVICE_USER="$USER"
    SYSTEMCTL_CMD="systemctl --user"
else
    SYSTEMD_DIR="/etc/systemd/system"
    LOG_DIR="/var/log/codex-dreams"
    DATA_DIR="/var/lib/codex-dreams"
    SYSTEMCTL_CMD="systemctl"

    # Check for root privileges
    if [ "$EUID" -ne 0 ]; then
        echo "Error: System service installation requires sudo privileges"
        exit 1
    fi
fi

SERVICE_PATH="$SYSTEMD_DIR/$SERVICE_FILE"

# Create directories
mkdir -p "$SYSTEMD_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

# Find Python executable
PYTHON_EXE=""
for candidate in "/usr/bin/python3" "/usr/local/bin/python3" "python3"; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON_EXE="$(command -v "$candidate")"
        break
    fi
done

if [ -z "$PYTHON_EXE" ]; then
    echo "Error: Could not find Python 3 executable"
    exit 1
fi

echo "Using Python: $PYTHON_EXE"

# Create service user for system installation
if [ "$USER_MODE" = false ] && [ "$SERVICE_USER" != "root" ]; then
    if ! id "$SERVICE_USER" >/dev/null 2>&1; then
        echo "Creating service user: $SERVICE_USER"
        useradd --system --shell /bin/false --home-dir "$DATA_DIR" --create-home "$SERVICE_USER"
    fi
fi

# Copy project files for system installation
if [ "$USER_MODE" = false ] && [ "$PROJECT_DIR" != "$INSTALL_DIR" ]; then
    echo "Copying project files to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chmod -R 755 "$INSTALL_DIR"
fi

# Set ownership for directories
if [ "$USER_MODE" = false ]; then
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR" "$DATA_DIR"
    chmod 755 "$LOG_DIR" "$DATA_DIR"
fi

# Check if service already exists
if [ -f "$SERVICE_PATH" ] && [ "$FORCE" != true ]; then
    echo "Error: Service already exists at $SERVICE_PATH"
    echo "Use --force to overwrite, or uninstall first with:"
    echo "  $SYSTEMCTL_CMD stop $SERVICE_NAME"
    echo "  $SYSTEMCTL_CMD disable $SERVICE_NAME"
    exit 1
fi

# Stop existing service if running
if $SYSTEMCTL_CMD is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "Stopping existing service..."
    $SYSTEMCTL_CMD stop "$SERVICE_NAME"
fi

# Disable existing service if enabled
if $SYSTEMCTL_CMD is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "Disabling existing service..."
    $SYSTEMCTL_CMD disable "$SERVICE_NAME"
fi

# Create service file
cat > "$SERVICE_PATH" << EOF
[Unit]
Description=Codex Dreams Insights Generation Daemon
Documentation=https://github.com/ladvien/codex-dreams
After=network.target network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$SERVICE_USER
EOF

# Add Group only for system services with non-root user
if [ "$USER_MODE" = false ] && [ "$SERVICE_USER" != "root" ]; then
    echo "Group=$SERVICE_USER" >> "$SERVICE_PATH"
fi

cat >> "$SERVICE_PATH" << EOF

# Service configuration
ExecStart=$PYTHON_EXE -m src.daemon.scheduler --daemon
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
Restart=always
RestartSec=10
TimeoutStartSec=0

# Working directory
WorkingDirectory=$INSTALL_DIR

# Environment
Environment=PYTHONPATH=$INSTALL_DIR
EnvironmentFile=-/etc/codex-dreams/daemon.env

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=codex-dreams-daemon
EOF

# Add security settings for system services
if [ "$USER_MODE" = false ]; then
    cat >> "$SERVICE_PATH" << EOF

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR $LOG_DIR $DATA_DIR
PrivateTmp=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictRealtime=true
LockPersonality=true
RestrictNamespaces=true
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM
EOF
fi

cat >> "$SERVICE_PATH" << EOF

[Install]
WantedBy=multi-user.target
EOF

# Set appropriate permissions
if [ "$USER_MODE" = true ]; then
    chmod 644 "$SERVICE_PATH"
else
    chown root:root "$SERVICE_PATH"
    chmod 644 "$SERVICE_PATH"
fi

# Reload systemd
echo "Reloading systemd..."
$SYSTEMCTL_CMD daemon-reload

# Enable the service
echo "Enabling service..."
$SYSTEMCTL_CMD enable "$SERVICE_NAME"

echo ""
echo "✅ Successfully installed Codex Dreams Daemon service!"
echo ""
echo "Service Details:"
echo "  Name: $SERVICE_NAME"
echo "  File: $SERVICE_PATH"
echo "  User: $SERVICE_USER"
echo "  Install Dir: $INSTALL_DIR"
echo "  Logs: $LOG_DIR (also available via journalctl)"
echo ""
echo "Management Commands:"
echo "  Start:   $SYSTEMCTL_CMD start $SERVICE_NAME"
echo "  Stop:    $SYSTEMCTL_CMD stop $SERVICE_NAME"
echo "  Status:  $SYSTEMCTL_CMD status $SERVICE_NAME"
echo "  Logs:    journalctl -u $SERVICE_NAME -f"
echo "  Enable:  $SYSTEMCTL_CMD enable $SERVICE_NAME"
echo "  Disable: $SYSTEMCTL_CMD disable $SERVICE_NAME"
echo ""
echo "The service is now enabled and will start automatically at boot."
echo "To start it now, run: $SYSTEMCTL_CMD start $SERVICE_NAME"