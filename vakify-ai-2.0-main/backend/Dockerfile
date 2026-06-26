FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV APP_ENV=production
ENV PORT=10000

EXPOSE 10000

CMD ["sh", "-c", "gunicorn -w 3 -k gthread --threads 4 -b 0.0.0.0:${PORT} wsgi:app"]
