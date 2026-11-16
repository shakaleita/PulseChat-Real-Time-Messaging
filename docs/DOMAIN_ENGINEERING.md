# PulseChat engineering notes

- Persistent messages, searchable room history and WebSocket notifications.
- WebSocket now requires a valid owner session and an allowed browser origin.
- Message payloads are length-validated to reduce abuse.
- This is a single-owner local demo, not a Slack-scale messaging deployment.
