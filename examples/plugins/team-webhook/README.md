# Team Webhook Notification Plugin

An integration plugin that sends real-time build notifications and progress updates to team communication platforms via webhooks (Slack, Discord, Microsoft Teams, or any custom webhook endpoint).

## Overview

This plugin hooks into Auto Code's build lifecycle and sends notifications to your team's communication platform. It keeps your team informed about build progress without requiring them to check logs or the dashboard constantly.

## What It Does

- **Build Start Notifications**: Alerts when a new build begins
- **Build Completion Notifications**: Reports success/failure with duration
- **Subtask Progress Updates**: Optional real-time subtask status changes
- **Multi-Platform Support**: Slack, Discord, Microsoft Teams, or generic webhooks
- **Duration Tracking**: Calculates and reports build times
- **Error Resilient**: Never blocks builds even if webhook delivery fails

## Features Demonstrated

### IntegrationPlugin Capabilities

- `on_load()` - Validates webhook URL configuration
- `on_enable()` - Loads configuration from environment
- `on_disable()` - Cleanup and resource release
- `on_unload()` - Final cleanup
- `is_available()` - Checks if plugin is ready to use

### Build Lifecycle Hooks

- `on_build_start()` - Sends "Build Started" notification
- `on_build_complete()` - Sends "Build Completed" with results and duration
- `on_subtask_update()` - Optionally sends subtask progress updates

### State Management

- Persists build start time for duration calculation
- Tracks notification count
- Maintains build success/failure status

## Installation

### From Directory

1. **Copy the plugin directory**:
   ```bash
   cp -r examples/plugins/team-webhook ~/.auto-claude/plugins/user/
   ```

2. **Configure your webhook URL** in `apps/backend/.env`:
   ```bash
   # Required: Your webhook endpoint URL
   TEAM_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

   # Optional: Enable subtask notifications (default: false)
   TEAM_WEBHOOK_NOTIFY_SUBTASKS=true

   # Optional: Webhook format (slack, discord, teams, generic)
   TEAM_WEBHOOK_FORMAT=slack
   ```

3. **Using the Electron UI**:
   - Open Auto Code desktop app
   - Navigate to **Plugins** (shortcut: `U`)
   - Click **Install Plugin**
   - Select **Directory** as installation source
   - Browse to `examples/plugins/team-webhook`
   - Click **Install**

4. **Enable the plugin**:
   - Find `team-webhook` in the plugins list
   - Click **Enable**

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TEAM_WEBHOOK_URL` | Webhook endpoint URL | `https://hooks.slack.com/services/T00/B00/XXX` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEAM_WEBHOOK_NOTIFY_SUBTASKS` | `false` | Set to `true` to enable subtask notifications |
| `TEAM_WEBHOOK_FORMAT` | `generic` | Webhook format: `slack`, `discord`, `teams`, or `generic` |

## Webhook Setup Guides

### Slack

1. Go to [Slack API: Incoming Webhooks](https://api.slack.com/messaging/webhooks)
2. Click **Create your Slack app**
3. Enable **Incoming Webhooks**
4. Click **Add New Webhook to Workspace**
5. Select a channel and authorize
6. Copy the webhook URL

```bash
TEAM_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX
TEAM_WEBHOOK_FORMAT=slack
```

**Slack Notification Example:**
```
🚀 Build Started: feature-auth
Project: my-app
Spec: feature-auth
Started: 2024-01-15 10:30:00
```

### Discord

1. Open your Discord server
2. Go to **Server Settings** → **Integrations** → **Webhooks**
3. Click **New Webhook**
4. Name it (e.g., "Auto Code Builds")
5. Select a channel
6. Copy the webhook URL

```bash
TEAM_WEBHOOK_URL=https://discord.com/api/webhooks/1234567890/XXXXXXXXXXXX
TEAM_WEBHOOK_FORMAT=discord
```

**Discord Notification Example:**
```
✅ Build Succeeded: feature-auth

Project: my-app
Spec: feature-auth
Status: SUCCEEDED
Duration: 5m 23s
Completed: 2024-01-15 10:35:23
```

### Microsoft Teams

1. Open your Teams channel
2. Click **⋯** (More options) → **Connectors**
3. Search for **Incoming Webhook**
4. Click **Configure**
5. Name it and optionally add an image
6. Copy the webhook URL

```bash
TEAM_WEBHOOK_URL=https://outlook.office.com/webhook/XXXXXXXX@XXXXXXXX/IncomingWebhook/XXXXXXXXXXXX
TEAM_WEBHOOK_FORMAT=teams
```

**Teams Notification Example:**
```
❌ Build Failed: feature-auth

Project: my-app
Spec: feature-auth
Status: FAILED
Duration: 2m 45s
Completed: 2024-01-15 10:33:15
```

### Generic/Custom Webhooks

For custom webhook endpoints, use the generic format:

```bash
TEAM_WEBHOOK_URL=https://your-api.com/webhooks/builds
TEAM_WEBHOOK_FORMAT=generic
```

**Generic Format Payload:**
```json
{
  "title": "🚀 Build Started: feature-auth",
  "message": "**Project:** my-app\n**Spec:** feature-auth\n**Started:** 2024-01-15 10:30:00",
  "color": "info",
  "timestamp": "2024-01-15T10:30:00",
  "source": "auto-code"
}
```

## Usage

Once configured and enabled, the plugin automatically sends notifications:

### Build Start
```
🚀 Build Started: feature-authentication

Project: ecommerce-platform
Spec: feature-authentication
Started: 2024-01-15 10:30:00
```

### Build Success
```
✅ Build Succeeded: feature-authentication

Project: ecommerce-platform
Spec: feature-authentication
Status: SUCCEEDED
Duration: 8m 42s
Completed: 2024-01-15 10:38:42
```

### Build Failure
```
❌ Build Failed: feature-authentication

Project: ecommerce-platform
Spec: feature-authentication
Status: FAILED
Duration: 3m 15s
Completed: 2024-01-15 10:33:15
```

### Subtask Updates (if enabled)
```
🔄 Subtask Update: subtask-2-1

Spec: feature-authentication
Subtask: subtask-2-1
Status: in_progress
```

```
✅ Subtask Update: subtask-2-1

Spec: feature-authentication
Subtask: subtask-2-1
Status: completed
```

## Subtask Notifications

By default, subtask notifications are **disabled** to reduce noise. To enable:

```bash
TEAM_WEBHOOK_NOTIFY_SUBTASKS=true
```

**When to enable subtask notifications:**
- Long-running builds with many subtasks
- You want real-time progress updates
- Team members are actively monitoring builds

**When to keep them disabled:**
- Short builds (< 10 minutes)
- Too many notifications become noise
- You only care about start/complete events

## Notification Colors

The plugin uses color-coding to indicate status:

| Status | Slack | Discord | Teams | Meaning |
|--------|-------|---------|-------|---------|
| Info (Build Start) | Blue | Blue | Blue | Build started |
| Success | Green | Green | Green | Build succeeded |
| Error | Red | Red | Red | Build failed |
| Warning | Yellow | Yellow | Orange | Warning state |

## Customizing Notifications

To customize notification content, edit `plugin.py`:

### Change Message Format

```python
def on_build_start(self, context: IntegrationContext) -> None:
    title = f"🚀 Starting build for {context.spec_name}"
    message = (
        f"**Spec:** {context.spec_name}\n"
        f"**Project:** {context.project_name}\n"
        f"**Branch:** {context.get_state('git_branch', 'main')}\n"
        f"**Triggered by:** {context.get_state('user', 'Unknown')}"
    )
    payload = self._format_message(title, message, "info")
    self._send_webhook(payload)
```

### Add Custom Fields

```python
# In Slack format
return {
    "attachments": [
        {
            "title": title,
            "text": message,
            "color": color_map.get(color, "#36a64f"),
            "fields": [
                {"title": "Environment", "value": "Production", "short": True},
                {"title": "Version", "value": "v2.3.0", "short": True}
            ],
            "footer": "Auto Code",
            "ts": int(datetime.now().timestamp())
        }
    ]
}
```

## Permissions

This plugin requires:

- **network_access**: To send HTTP POST requests to the webhook endpoint

## Troubleshooting

### Notifications not appearing

1. **Check if plugin is enabled** (not just installed)
2. **Verify webhook URL** is correct:
   ```bash
   curl -X POST -H "Content-Type: application/json" \
     -d '{"text":"Test from Auto Code"}' \
     $TEAM_WEBHOOK_URL
   ```
3. **Check logs** for error messages
4. **Verify the webhook format** matches your platform

### "No webhook URL configured" warning

- Ensure `TEAM_WEBHOOK_URL` is set in `apps/backend/.env`
- Restart the application after adding the variable

### Webhook returns 400 Bad Request

- The payload format might not match your platform
- Try using `TEAM_WEBHOOK_FORMAT=generic`
- Check your platform's webhook documentation

### Network timeout errors

- The webhook endpoint might be slow or unreachable
- Increase timeout in plugin code (default: 10 seconds)
- Check your network/firewall settings

### Too many notifications

- Disable subtask notifications: `TEAM_WEBHOOK_NOTIFY_SUBTASKS=false`
- Consider using a filter based on spec name or project

## Advanced Usage

### Multiple Webhooks

To send to multiple channels, create multiple plugin instances:

```bash
# Channel 1: All builds
TEAM_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/XXX1
TEAM_WEBHOOK_FORMAT=slack

# Channel 2: Production builds only (implement in plugin)
TEAM_WEBHOOK_URL_PROD=https://hooks.slack.com/services/T00/B00/XXX2
```

### Conditional Notifications

Add logic to filter notifications:

```python
def on_build_start(self, context: IntegrationContext) -> None:
    # Only notify for production specs
    if "prod" not in context.spec_name.lower():
        return

    # Send notification
    ...
```

### Rich Notifications with Mentions

```python
# Slack: Mention users on failure
if not success:
    message += "\n\n<@U12345678> Build failed, please check!"
```

## Learn More

- [Integration Plugin Development Guide](../../../guides/plugins/integration-plugins.md)
- [Plugin SDK Reference](../../../apps/backend/plugins/sdk/integration.py)
- [Webhook Formats Documentation](../../../docs/webhook-formats.md)

## License

MIT - See LICENSE file for details
