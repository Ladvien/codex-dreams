# Codex Dreams Daemon

A cross-platform daemon solution for automatically running insights generation on a schedule.

## Features

- ✅ **Cross-platform**: Works on Windows, macOS, and Linux
- ✅ **Easy installation**: Single command service installation  
- ✅ **Configurable**: JSON configuration with environment variable support
- ✅ **Robust**: Retry logic, error handling, and crash recovery
- ✅ **Monitored**: Built-in metrics and logging
- ✅ **Service management**: Start, stop, status commands
- ✅ **Security**: Runs with minimal privileges and restricted access

## Quick Start

### 1. Install Dependencies

```bash
# Install the project with daemon dependencies
pip install -e .

# Or install specific daemon dependencies
pip install psutil schedule
```

### 2. Create Configuration

```bash
# Create default configuration
codex-daemon config --init

# View configuration
codex-daemon config --show
```

### 3. Install as Service

```bash
# Install as system service (requires admin/sudo)
sudo codex-daemon install

# Or install as user service
codex-daemon install --user
```

### 4. Start the Service

```bash
# Start the service
codex-daemon start

# Check status
codex-daemon status
```

## Configuration

The daemon uses a JSON configuration file with environment variable support:

### Default Configuration Locations

- **Windows**: `%USERPROFILE%\AppData\Local\codex-dreams\daemon.json`
- **macOS**: `~/Library/Application Support/codex-dreams/daemon.json`  
- **Linux**: `~/.config/codex-dreams/daemon.json`

### Configuration Options

```json
{
  "interval_minutes": 5,
  "max_retries": 3,
  "retry_delay_seconds": 30,
  "log_level": "INFO",
  "log_file": null,
  "pid_file": null,
  "working_directory": null,
  "environment_file": null,
  "service_name": "codex-dreams-daemon",
  "service_description": "Codex Dreams Insights Generation Daemon"
}
```

### Environment Variables

You can override configuration with environment variables:

- `CODEX_INTERVAL_MINUTES`: Run interval (default: 5)
- `CODEX_LOG_LEVEL`: Logging level (default: INFO)
- `CODEX_LOG_FILE`: Log file path
- `CODEX_PID_FILE`: PID file path
- `CODEX_WORKING_DIR`: Working directory
- `CODEX_ENV_FILE`: Environment file (.env)
- `CODEX_MAX_RETRIES`: Maximum retry attempts
- `CODEX_RETRY_DELAY_SECONDS`: Delay between retries

Plus all the standard codex-dreams environment variables:
- `POSTGRES_DB_URL`: Database connection string
- `OLLAMA_URL`: Ollama server URL
- `OLLAMA_MODEL`: LLM model name
- `DUCKDB_PATH`: DuckDB database path

## Commands

### Installation and Service Management

```bash
# Install service (system-wide, requires admin)
sudo codex-daemon install

# Install as user service
codex-daemon install --user

# Uninstall service
codex-daemon uninstall

# Start service
codex-daemon start

# Stop service  
codex-daemon stop

# Check service status
codex-daemon status
```

### Testing and Development

```bash
# Run in foreground for testing
codex-daemon start --foreground

# Run insights generation once
codex-daemon run-once

# Validate configuration
codex-daemon config --validate
```

### Configuration Management

```bash
# Create default configuration
codex-daemon config --init

# Show current configuration
codex-daemon config --show

# Use custom config file
codex-daemon --config /path/to/config.json status
```

## Platform-Specific Details

### Windows

- Uses NSSM (Non-Sucking Service Manager) if available, otherwise PowerShell
- Service runs as Local System by default
- Logs to Windows Event Log and file
- Configuration stored in `%APPDATA%`

**Manual Installation Scripts:**
- `service_configs/windows/install-service.ps1`: PowerShell installation
- `service_configs/windows/codex-dreams-daemon.bat`: Service wrapper

### macOS

- Uses launchd for service management
- Supports both user and system launch agents
- Automatic restart on failure
- Logs to system log and file

**Manual Installation:**
```bash
# Copy and customize the plist file
cp service_configs/macos/com.codex-dreams.daemon.plist ~/Library/LaunchAgents/
# Edit paths in the plist file
launchctl load ~/Library/LaunchAgents/com.codex-dreams.daemon.plist
```

### Linux

- Uses systemd for service management
- Runs with restricted permissions and security features
- Supports both user and system services
- Integrated with journald for logging

**Manual Installation:**
```bash
# Use the installation script
sudo service_configs/linux/install-service.sh
```

## Logging and Monitoring

### Log Files

Default log locations:
- **Windows**: `%USERPROFILE%\AppData\Local\codex-dreams\logs\daemon.log`
- **macOS**: `~/Library/Logs/codex-dreams/daemon.log`
- **Linux**: `/var/log/codex-dreams/daemon.log` (system) or `~/.local/share/codex-dreams/logs/daemon.log` (user)

### Metrics

The daemon tracks and reports:
- Uptime and run statistics
- Success/failure rates
- Average runtime
- Error types and counts
- Last run times

View metrics with: `codex-daemon status`

### Log Levels

- `DEBUG`: Detailed execution information
- `INFO`: General operational messages (default)
- `WARNING`: Important issues that don't stop operation
- `ERROR`: Errors that prevent insights generation

## Troubleshooting

### Common Issues

1. **Permission denied during installation**
   ```bash
   # Use sudo for system services or --user flag
   sudo codex-daemon install
   # OR
   codex-daemon install --user
   ```

2. **Service won't start**
   ```bash
   # Check configuration
   codex-daemon config --validate
   
   # Test in foreground
   codex-daemon start --foreground
   
   # Check logs
   codex-daemon status
   ```

3. **Python not found**
   ```bash
   # Make sure Python is in PATH or activate virtual environment
   source venv/bin/activate  # Linux/macOS
   # OR
   venv\Scripts\activate.bat  # Windows
   ```

4. **Database connection issues**
   ```bash
   # Test database connection
   codex-daemon run-once
   
   # Check environment variables
   echo $POSTGRES_DB_URL
   echo $OLLAMA_URL
   ```

### Debug Mode

Run with debug logging:
```bash
codex-daemon --log-level DEBUG start --foreground
```

### Manual Service Management

If automatic service management fails, use platform-specific tools:

**Windows:**
```cmd
sc query codex-dreams-daemon
sc start codex-dreams-daemon
sc stop codex-dreams-daemon
```

**macOS:**
```bash
launchctl list | grep codex-dreams
launchctl start com.codex-dreams.daemon
launchctl stop com.codex-dreams.daemon
```

**Linux:**
```bash
systemctl status codex-dreams-daemon
systemctl start codex-dreams-daemon
systemctl stop codex-dreams-daemon
journalctl -u codex-dreams-daemon -f
```

## Security Considerations

- Services run with minimal required privileges
- File permissions are restricted appropriately
- No network services exposed
- Environment variables used for sensitive configuration
- Logs may contain database connection strings (use appropriate log file permissions)

## Development

### Project Structure

```
src/daemon/
├── __init__.py           # Package initialization
├── cli.py               # Command-line interface
├── config.py            # Configuration management
├── scheduler.py         # Core daemon scheduler
└── service_manager.py   # Cross-platform service management

service_configs/
├── windows/             # Windows service files
├── macos/              # macOS launchd files
└── linux/              # Linux systemd files
```

### Adding Features

1. **New configuration options**: Add to `DaemonConfig` in `config.py`
2. **Service management**: Extend `ServiceManager` in `service_manager.py`  
3. **Scheduling logic**: Modify `DaemonScheduler` in `scheduler.py`
4. **CLI commands**: Add to `cli.py`

### Testing

```bash
# Run tests
pytest tests/

# Test specific daemon functionality
pytest tests/ -k daemon

# Test installation (requires admin/sudo)
sudo python -m pytest tests/daemon/test_installation.py
```

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation
4. Test on multiple platforms when possible
5. Consider security implications

## License

GNU General Public License v3 (GPLv3) - see LICENSE file for details.