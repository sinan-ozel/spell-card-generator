FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fonts/ fonts/
COPY spell.py .
COPY main.py .
COPY plain.py .

CMD ["python", "main.py"]
