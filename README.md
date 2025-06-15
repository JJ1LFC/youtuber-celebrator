# YouTube Monitoring Bot

## Overview
A tool that monitors YouTube channel subscriber counts and playlist video view counts, detects milestones and playlist changes, and sends notifications to Discord.

## Requirements
- Python ≥ 3.8 (in Docker, 3.12 by default)
- Docker (optional)
- Docker Compose (optional)

## Environment Variables
Store these in a `.env` file or export in your shell:

```bash
YOUTUBE_API_KEY=<Your YouTube Data API v3 Key>
DISCORD_WEBHOOK_URL=<Your Discord Webhook URL>
```

## Configuration (`config.json`)

Prepare a `config.json` at the project root following this schema:

```json
{
  "subscriber_thresholds": [1000, 5000],
  "view_thresholds": [10000, 50000],
  "channels": [
    { "id": "UCxxxxxxxxxxxx", "desc": "Official Channel" }
  ],
  "playlists": [
    { "id": "PLxxxxxxxxxxxx", "desc": "New Releases" }
  ]
}
```

## Local One-Shot Execution

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
2. Export environment variables or use a `.env` file.
3. Run:

   ```bash
   python monitor.py
   ```

On first run, the script saves the initial state without sending notifications.

## Docker Compose for Continuous Monitoring

1. Build and start the service:

   ```bash
   docker compose up -d --build
   ```
2. The container will run the monitor script automatically.
  1. The first job runs once the container is running and does so every 00 minute of every hour.
3. Logs are handled by Docker and state written to `./data/data.json`.

To stop:

```bash
docker compose down
```

## Logs

All important steps and notifications are logged with timestamps.

```bash
tail -f monitor.log
```


