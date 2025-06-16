# YouTubeer Milestone Celebrating Bot

## Overview
A tool that monitors YouTube channel subscriber counts and playlist video view counts, detects milestones, and sends notifications to Discord (and optionally to Twitter).

## Requirements
- Python ≥ 3.8 (in Docker, 3.12 by default)
- Docker (optional)
- Docker Compose (optional)

## Preparation
You will need
- Google Cloud API Key with YouTube Data API v3 enabled
- Discord Webhook URL to which you would like to send notification
- (Optional) Twitter API v2 Keys of the account you would like to auto-post notification.

## Setup Environment Variables
Store these in a `.env` file:

```env
YOUTUBE_API_KEY=hoge
DISCORD_WEBHOOK_URL=hoge
TWITTER_CONSUMER_KEY=hoge
TWITTER_CONSUMER_SECRET=hoge
TWITTER_ACCESS_TOKEN=hoge
TWITTER_ACCESS_SECRET=hoge
```

## Configuration (`config.json`)

Prepare a `config.json` at the project root following `config.schema.json`:

> ***Do not set too small `view_thresholds` especially you are enabling Twitter.***
> If you set like [1, 2, 3] and the view counts jump from 0 to 5 in an hour, this script will post 3 Tweets at once, which may easiy hit Twitter API rate limit.

```json
{
  "subscriber_thresholds": [1000, 5000],
  "view_thresholds": [10000, 50000],
  "channels": [
    {
      "id": "UCxxxxxxxxxxxx",
      "desc": "Official Channel",
      "twitter_enabled": false
    }
  ],
  "playlists": [
    {
    "id": "PLxxxxxxxxxxxx",
    "desc": "New Releases",
    "twitter_enabled": true}
  ]
}
```

## Execution

1. Build and start the service:

   ```bash
   docker compose up -d --build
   ```
2. The container will run the initial scan for the first time. This time the script will not send any notification eather to Discord/Twitter.
3. After the initial scan, states are saved to `data/data.json` and re-runs at 00 minute of every hour.

To stop:

```bash
docker compose down
```

