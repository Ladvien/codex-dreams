#!/bin/bash

# Setup log rotation for biological memory system
# Prevents disk space issues from continuous logging

set -e

# Determine project directory relative to script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"

# Create necessary directories
mkdir -p "$LOG_DIR/biological_rhythms"
mkdir -p "$LOG_DIR/archive"

# Create logrotate configuration with relative paths
cat > "$PROJECT_DIR/logrotate.conf" << EOF
# Biological Memory System Log Rotation Configuration
# Note: Update paths based on your installation directory

# Main cron log
$LOG_DIR/cron.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644
    postrotate
        echo "[\$(date)] Log rotated" >> $LOG_DIR/rotation.log
    endscript
}

# Biological rhythm logs
$LOG_DIR/biological_rhythms/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    maxage 30
    create 644
    olddir $LOG_DIR/archive
    postrotate
        # Clean up very old compressed logs
        find $LOG_DIR/archive -name "*.gz" -mtime +60 -delete
    endscript
}

# dbt logs
$LOG_DIR/dbt.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 644
}
EOF

echo "Log rotation configuration created at: $PROJECT_DIR/logrotate.conf"

# Add to crontab (runs daily at 2 AM)
CRON_ENTRY="0 2 * * * /usr/local/opt/logrotate/sbin/logrotate -s $PROJECT_DIR/logrotate.state $PROJECT_DIR/logrotate.conf"

# Check if logrotate is installed
if ! command -v logrotate &> /dev/null; then
    echo "Warning: logrotate is not installed. On macOS, install with:"
    echo "  brew install logrotate"
    echo ""
    echo "After installation, add this to your crontab:"
    echo "  $CRON_ENTRY"
else
    echo "Logrotate is installed."
    echo ""
    echo "To enable automatic log rotation, add this to your crontab:"
    echo "  crontab -e"
    echo "  # Add the following line:"
    echo "  $CRON_ENTRY"
fi

# Create initial log files if they don't exist
touch "$LOG_DIR/cron.log"
touch "$LOG_DIR/rotation.log"
touch "$LOG_DIR/dbt.log"

echo ""
echo "Log rotation setup complete!"
echo "Logs will be:"
echo "  - Rotated daily (cron.log, biological_rhythms/*.log)"
echo "  - Rotated weekly (dbt.log)"
echo "  - Compressed after 1 day"
echo "  - Archived in $LOG_DIR/archive"
echo "  - Deleted after 60 days (compressed archives)"
