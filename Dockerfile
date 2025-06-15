FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY monitor.py config.json ./
CMD ["python3", "./monitor.py"]

