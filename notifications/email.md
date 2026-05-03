# Email Notification Template

## Trigger
Events with `email` channel enabled in `notification-policy.json`.
Disabled by default. Requires SMTP environment variables.

## Required Environment Variables
- `SMTP_HOST` — SMTP server hostname
- `SMTP_PORT` — SMTP server port (default: 587)
- `SMTP_USER` — SMTP username
- `SMTP_PASSWORD` — SMTP password (never stored in repo)
- `NOTIFICATION_EMAIL` — Recipient email address

## Subject Template
```
[SimFlow {level}] {event_type}: {workflow_id}
```

## Body Template
```
SimFlow Notification
====================

Event:     {event_type}
Level:     {level}
Workflow:  {workflow_id}
Stage:     {stage_name}
Time:      {timestamp}

Details:
{message}

{details}

---
This is an automated notification from SimFlow.
Do not reply to this email.
```

## Security Notes
- SMTP credentials are read from environment variables only
- Credentials are never written to artifacts, logs, or state files
- Email content does not include file paths or sensitive data
