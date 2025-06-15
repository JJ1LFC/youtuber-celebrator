FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update && apt-get install -y cron \
    && rm -rf /var/lib/apt/lists/*
COPY monitor.py config.json youtuber-monitor.cron ./
RUN chmod 0644 youtuber-monitor.cron \
    && mv youtuber-monitor.cron /etc/cron.d/youtuber-monitor \
    && crontab /etc/cron.d/youtuber-monitor
CMD ["cron", "-f"]
#CMD ["python3", "./monitor.py", ">>", "/app/log/monitor.log", "2>&1"]

