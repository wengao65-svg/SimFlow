# Webhook Notification Template

## Trigger
Events with `webhook` channel enabled in `notification-policy.json`.
Disabled by default. Requires `SIMFLOW_WEBHOOK_URL` environment variable.

## Required Environment Variables
- `SIMFLOW_WEBHOOK_URL` — Webhook endpoint URL

## Payload Template (JSON)
```json
{
  "event": "{event_type}",
  "level": "{level}",
  "workflow_id": "{workflow_id}",
  "stage": "{stage_name}",
  "timestamp": "{timestamp}",
  "message": "{message}",
  "details": {
    "artifacts": [],
    "checkpoint_id": null,
    "error": null
  },
  "source": "simflow",
  "version": "0.1.0"
}
```

## HTTP Headers
```
Content-Type: application/json
X-SimFlow-Event: {event_type}
X-SimFlow-Workflow: {workflow_id}
```

## Security Notes
- Webhook URL is read from environment variables only
- No credentials or tokens are included in the payload
- Use HTTPS endpoints in production
- Consider adding HMAC signature for payload verification
