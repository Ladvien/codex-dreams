#!/bin/bash
# Biological Memory Orchestrator Management Script - BMP-008

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORCHESTRATOR_SCRIPT="$SCRIPT_DIR/orchestrate_biological_memory.py"
PIDFILE="/var/run/biological_memory_orchestrator.pid"
LOGDIR="/var/log/biological_memory"

# Ensure log directory exists
mkdir -p "$LOGDIR"

case "$1" in
    start)
        echo "Starting Biological Memory Orchestrator..."
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "Orchestrator is already running (PID: $(cat "$PIDFILE"))"
            exit 1
        fi
        
        # Start the orchestrator in background
        nohup python3 "$ORCHESTRATOR_SCRIPT" > "$LOGDIR/orchestrator_startup.log" 2>&1 &
        echo $! > "$PIDFILE"
        echo "Orchestrator started (PID: $!)"
        ;;
        
    stop)
        echo "Stopping Biological Memory Orchestrator..."
        if [ -f "$PIDFILE" ]; then
            PID=$(cat "$PIDFILE")
            if kill -0 "$PID" 2>/dev/null; then
                kill -TERM "$PID"
                echo "Sent SIGTERM to PID $PID"
                
                # Wait for graceful shutdown
                for i in {1..10}; do
                    if ! kill -0 "$PID" 2>/dev/null; then
                        echo "Orchestrator stopped gracefully"
                        rm -f "$PIDFILE"
                        exit 0
                    fi
                    sleep 1
                done
                
                # Force kill if still running
                if kill -0 "$PID" 2>/dev/null; then
                    kill -KILL "$PID"
                    echo "Orchestrator force-stopped"
                fi
            else
                echo "Orchestrator not running (stale PID file)"
            fi
            rm -f "$PIDFILE"
        else
            echo "Orchestrator not running (no PID file)"
        fi
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "Biological Memory Orchestrator is running (PID: $(cat "$PIDFILE"))"
            
            # Show recent log entries
            echo "Recent log entries:"
            tail -n 5 "$LOGDIR/orchestrator.log" 2>/dev/null || echo "No log entries found"
        else
            echo "Biological Memory Orchestrator is not running"
            if [ -f "$PIDFILE" ]; then
                echo "Removing stale PID file"
                rm -f "$PIDFILE"
            fi
        fi
        ;;
        
    logs)
        echo "=== Orchestrator Logs ==="
        tail -f "$LOGDIR/orchestrator.log"
        ;;
        
    health)
        echo "=== Biological Memory Health Check ==="
        python3 -c "
import sys
sys.path.append('$SCRIPT_DIR')
from orchestrate_biological_memory import BiologicalMemoryOrchestrator

orchestrator = BiologicalMemoryOrchestrator()
if orchestrator.health_check():
    print('Health check: PASSED')
    sys.exit(0)
else:
    print('Health check: FAILED')
    sys.exit(1)
"
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the biological memory orchestrator"
        echo "  stop    - Stop the orchestrator gracefully"  
        echo "  restart - Restart the orchestrator"
        echo "  status  - Show orchestrator status and recent logs"
        echo "  logs    - Follow orchestrator logs in real-time"
        echo "  health  - Run health check on biological memory system"
        exit 1
        ;;
esac