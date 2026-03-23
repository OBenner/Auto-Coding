# Auto Claude Server Deployment Files

This directory contains systemd service and configuration templates for deploying the Auto Claude Web Backend as a system service on Linux.

## Files

| File | Description |
|------|-------------|
| `auto-claude-server.service` | systemd unit file for the web backend service |
| `auto-claude-server.conf` | Environment configuration template |

## Quick Install

### 1. Create system user

```bash
sudo useradd --system --no-create-home --shell /sbin/nologin auto-claude
```

### 2. Install application

```bash
sudo mkdir -p /opt/auto-claude
sudo cp -r . /opt/auto-claude/apps/web-backend
sudo chown -R auto-claude:auto-claude /opt/auto-claude

# Create virtual environment and install dependencies
sudo -u auto-claude python3 -m venv /opt/auto-claude/apps/web-backend/venv
sudo -u auto-claude /opt/auto-claude/apps/web-backend/venv/bin/pip install -r /opt/auto-claude/apps/web-backend/requirements.txt
```

### 3. Configure environment

```bash
sudo mkdir -p /etc/auto-claude
sudo cp deploy/auto-claude-server.conf /etc/auto-claude/auto-claude-server.conf
sudo chmod 640 /etc/auto-claude/auto-claude-server.conf
sudo chown root:auto-claude /etc/auto-claude/auto-claude-server.conf

# Edit configuration - especially SECRET_KEY and CLAUDE_CODE_OAUTH_TOKEN
sudo nano /etc/auto-claude/auto-claude-server.conf
```

**Generate a secure SECRET_KEY:**
```bash
openssl rand -hex 32
```

**Get your Claude OAuth token:**
```bash
claude setup-token --print
```

### 4. Set up logging directory

```bash
sudo mkdir -p /var/log/auto-claude
sudo chown auto-claude:auto-claude /var/log/auto-claude
```

### 5. Set up data directory

```bash
sudo mkdir -p /opt/auto-claude/.auto-claude
sudo chown auto-claude:auto-claude /opt/auto-claude/.auto-claude
```

### 6. Install and start the service

```bash
sudo cp deploy/auto-claude-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable auto-claude-server
sudo systemctl start auto-claude-server
```

### 7. Verify the service is running

```bash
sudo systemctl status auto-claude-server
curl http://localhost:8000/health
```

## Service Management

```bash
# Start / stop / restart
sudo systemctl start auto-claude-server
sudo systemctl stop auto-claude-server
sudo systemctl restart auto-claude-server

# Reload configuration without full restart (sends SIGHUP)
sudo systemctl reload auto-claude-server

# Enable / disable autostart on boot
sudo systemctl enable auto-claude-server
sudo systemctl disable auto-claude-server

# View live logs
sudo journalctl -u auto-claude-server -f

# View recent logs
sudo journalctl -u auto-claude-server --since "1 hour ago"
```

## Configuration Reference

See `auto-claude-server.conf` for all available settings with descriptions.

Key settings to configure for production:

| Setting | Description | Required |
|---------|-------------|----------|
| `SECRET_KEY` | JWT signing key — use `openssl rand -hex 32` | **Yes** |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude OAuth token for agent sessions | **Yes** |
| `CORS_ORIGINS` | Allowed frontend origins | **Yes** |
| `HOST` | Bind address (default: `0.0.0.0`) | No |
| `PORT` | Listen port (default: `8000`) | No |
| `WORKERS` | Uvicorn worker count (default: `4`) | No |
| `DEBUG` | Enable debug mode — **set `false` in production** | No |
| `LOG_LEVEL` | Logging verbosity (default: `info`) | No |

## Security Notes

- The service runs as the `auto-claude` system user (no login shell, no home directory)
- `NoNewPrivileges=true` prevents privilege escalation
- `PrivateTmp=true` isolates `/tmp` from other services
- `ProtectSystem=strict` makes most of the filesystem read-only
- The config file at `/etc/auto-claude/auto-claude-server.conf` should be readable only by `root` and `auto-claude` (mode `640`)
- Never commit `SECRET_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` to version control

## Updating

```bash
# Pull new code
cd /opt/auto-claude
sudo git pull

# Install any new dependencies
sudo -u auto-claude /opt/auto-claude/apps/web-backend/venv/bin/pip install -r /opt/auto-claude/apps/web-backend/requirements.txt

# Restart the service
sudo systemctl restart auto-claude-server
```

## Troubleshooting

**Service fails to start:**
```bash
sudo journalctl -u auto-claude-server -n 50 --no-pager
```

**Permission denied errors:**
Check that `/opt/auto-claude` and `/var/log/auto-claude` are owned by the `auto-claude` user.

**Port already in use:**
Change `PORT` in `/etc/auto-claude/auto-claude-server.conf` or stop the conflicting service.

**Authentication errors:**
Verify `CLAUDE_CODE_OAUTH_TOKEN` is set and valid. Re-generate with:
```bash
claude setup-token --print
```

For more detailed deployment instructions, see [DEPLOYMENT.md](../DEPLOYMENT.md).
