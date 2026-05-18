FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*
COPY main.py .
RUN pip install --no-cache-dir pyTelegramBotAPI requests python-dotenv google-generativeai
CMD ["python", "main.py"]
