FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fonts/ fonts/
COPY template/ template/
COPY spell.py .
COPY main.py .
COPY server.py .
COPY plain.py .

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
