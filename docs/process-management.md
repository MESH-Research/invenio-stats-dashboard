# Process Management for Long-Running CLI Commands

This document describes how to use the new process management features for running long-running CLI commands in the background with full monitoring and control capabilities.

## Overview

The process management system provides:

- **Background execution** of long-running commands
- **Process monitoring** with real-time status updates
- **Graceful cancellation** with configurable timeouts
- **PID file management** for process tracking
- **Log file capture** for debugging and monitoring

## New CLI Commands

### 1. `migrate-events-background`

Start event migration in the background with full process management.

```bash
# Basic background migration
invenio community-stats migrate-events-background

# With custom parameters
invenio community-stats migrate-events-background \
  --event-types view download \
  --batch-size 500 \
  --max-memory-percent 70 \
  --max-batches 100 \
  --delete-old-indices

# Custom PID directory
invenio community-stats migrate-events-background \
  --pid-dir /var/run/invenio-community-stats
```

**Features:**
- Runs the same migration logic as `migrate-events` but in background
- Creates PID files for process tracking
- Captures all output to log files
- Provides immediate feedback with monitoring commands

### 2. `process-status`

Monitor the status of a running background process.

```bash
# Basic status
invenio community-stats process-status event-migration

# With log output
invenio community-stats process-status event-migration --show-log

# Custom log lines
invenio community-stats process-status event-migration --show-log --log-lines 50

# Custom PID directory
invenio community-stats process-status event-migration --pid-dir /var/run/kcworks
```

**Output includes:**
- Process ID (PID)
- Current status
- Runtime duration
- Progress percentage (if available)
- Current task description
- Recent log output (optional)

### 3. `cancel-process`

Gracefully cancel a running background process.

```bash
# Basic cancellation
invenio community-stats cancel-process event-migration

# With custom timeout
invenio community-stats cancel-process event-migration --timeout 60

# Custom PID directory
invenio community-stats cancel-process event-migration --pid-dir /var/run/kcworks
```

**Cancellation process:**
1. Sends SIGTERM for graceful shutdown
2. Waits for specified timeout (default: 30 seconds)
3. If graceful shutdown fails, sends SIGKILL
4. Cleans up PID and status files

### 4. `list-processes`

List all currently running background processes.

```bash
# List all processes
invenio community-stats list-processes

# Custom PID directory
invenio community-stats list-processes --pid-dir /var/run/kcworks
```

**Output:**
- List of running process names
- Total count
- Helpful commands for monitoring and control

## File Structure

The process manager creates the following files in the PID directory (default: `/tmp`):

```
/tmp/
├── invenio-community-stats-event-migration.pid      # Process ID
├── invenio-community-stats-event-migration.status   # JSON status information
└── invenio-community-stats-event-migration.log      # Process output and logs
```

### Status File Format

```json
{
  "pid": 12345,
  "start_time": 1640995200.0,
  "status": "running",
  "command": "invenio community-stats migrate-events --batch-size 1000",
  "progress": 45.2,
  "current_task": "Processing batch 23 of 50",
  "last_update": 1640995260.0
}
```

## Use Cases

### 1. Long-Running Migrations

```bash
# Start migration in background
invenio community-stats migrate-events-background \
  --event-types view download \
  --batch-size 1000

# Check progress periodically
invenio community-stats process-status event-migration

# Monitor with logs
invenio community-stats process-status event-migration --show-log

# Cancel if needed
invenio community-stats cancel-process event-migration
```

### 2. Production Deployments

```bash
# Use custom PID directory for production
invenio community-stats migrate-events-background \
  --pid-dir /var/run/invenio-community-stats \
  --batch-size 500 \
  --max-memory-percent 60

# Monitor from different terminal
invenio community-stats process-status event-migration --pid-dir /var/run/invenio-community-stats

# List all running processes
invenio community-stats list-processes --pid-dir /var/run/invenio-community-stats
```

### 3. Development and Testing

```bash
# Start with limited batches for testing
invenio community-stats migrate-events-background \
  --max-batches 10 \
  --batch-size 100

# Monitor progress
watch -n 5 'invenio community-stats process-status event-migration'

# Cancel when done testing
invenio community-stats cancel-process event-migration
```

## Best Practices

### 1. PID Directory Management

- Use `/tmp` for development and testing
- Use `/var/run/invenio-community-stats` for production deployments
- Ensure the directory is writable by the application user
- Consider using systemd-managed directories for system services

### 2. Monitoring Strategy

- Check status every 5-10 minutes for long migrations
- Use `--show-log` to debug issues
- Monitor system resources (memory, CPU) alongside process status
- Set up alerts for failed or stuck processes

### 3. Cancellation Strategy

- Use default 30-second timeout for most cases
- Increase timeout for processes that need graceful cleanup
- Monitor logs during cancellation to ensure proper shutdown
- Check for orphaned processes if cancellation fails

### 4. Error Handling

- Always check process status after starting
- Monitor logs for errors and warnings
- Have a plan for handling interrupted migrations
- Use `migrate-month` to resume specific monthly indices

## Troubleshooting

### Process Not Found

```bash
# Check if process is actually running
ps aux | grep event-migration

# Check PID file
cat /tmp/event-migration.pid

# Clean up stale files
rm -f /tmp/event-migration.*
```

### Permission Issues

```bash
# Check directory permissions
ls -la /tmp/event-migration.*

# Ensure proper user ownership
sudo chown kcworks:kcworks /tmp/event-migration.*
```

### Stuck Processes

```bash
# Check process status
invenio community-stats process-status event-migration

# Force kill if needed
sudo kill -9 $(cat /tmp/event-migration.pid)

# Clean up files
rm -f /tmp/event-migration.*
```

## Integration with Existing Commands

The new process management commands complement the existing CLI:

- `migrate-events` - Synchronous execution (existing)
- `migrate-events-background` - Background execution with management (new)
- `migration-status` - Overall migration status (existing)
- `process-status` - Background process status (new)

## Dependencies

- `psutil>=5.9.0` - Process management and monitoring
- Standard Python libraries: `subprocess`, `pathlib`, `json`, `time`

## Security Considerations

- PID files contain process IDs and command information
- Log files may contain sensitive data
- Ensure proper file permissions and access controls
- Consider using dedicated directories for production deployments
- Monitor and rotate log files to prevent disk space issues
