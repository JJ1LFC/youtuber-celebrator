# YouTubeer Milestone Celebrating Bot 🎉

[![Python ≥3.8](https://img.shields.io/badge/python-%3E%3D3.8-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-supported-blue)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Overview

A tool that monitors:

- YouTube **channel** subscriber counts
- YouTube **playlist** video view counts

Detects milestone thresholds and sends notifications to:

- **Discord** (via webhook)
- **Twitter** (optional, via API v2)

Ideal for content creators or community managers who want automatic alerts when key metrics are reached.

---

## Features

- ✅ Monitor multiple channels & playlists
- 🎯 Customizable subscriber & view thresholds
- 🔔 Discord notifications out-of-the-box
- 🐦 Optional Twitter auto-tweet
- ⚙️ Fully configurable via JSON + schema validation
- 📦 Docker-ready with a single command
- 📋 Detailed logs & adjustable verbosity

---

## Installation

```bash
git clone https://github.com/jj1lfc/youtuber-celebrator.git
cd youtuber-celebrator
```

### Requirements

- Python ≥ 3.8
- Docker & Docker Compose (optional)

---

## Configuration

### Environment Variables

Create a `.env` file at project root:

```ini
YOUTUBE_API_KEY=YOUR_GOOGLE_API_KEY
DISCORD_WEBHOOK_URL=YOUR_DISCORD_WEBHOOK
TWITTER_CONSUMER_KEY=...
TWITTER_CONSUMER_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
```

### Example (`config.json`)

```json
{
  "log_level": "DEBUG",
  "subscriber_thresholds": [1000, 5000, 10000],
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
      "twitter_enabled": true
    }
  ]
}
```

---

## Usage

### Docker (Recommended)

```bash
docker compose up -d --build
# Logs: docker compose logs -f
```

- **Initial run**: scans metrics but does _not_ notify.
- **Hourly**: re-runs at each `:00` minute and sends alerts.

To stop:

```bash
docker compose down
```

### From Source

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Run immediately
python bot.py
# Or schedule via cron:
0 * * * * /path/to/bot.py >> /var/log/ytbot.log 2>&1
```

---

## Logging

- Controlled via `log_level` in `config.json`.
- Levels: `DEBUG` → all logs, `INFO` → info+warn+error, etc.
- Format: `YYYY-MM-DDThh:mm:ss±zzzz [LEVEL] message`

---

## Scheduling

- Uses [`schedule`](https://pypi.org/project/schedule/)
- By default:
  - **At start**: runs once
  - **Every hour**: at `:00` via `schedule.every().hour.at(":00")`
- To disable initial run, remove the `main()` call under `if __name__ == "__main__"`.

---

## Troubleshooting

- Try increasing `log_level`.
- **Missing notifications**: verify your thresholds and check API keys.
- **Rate limits**: avoid very low thresholds to prevent burst tweets/discord posts.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

