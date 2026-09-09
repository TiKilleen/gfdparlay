FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
EXPOSE $PORT

CMD flask db upgrade && gunicorn -b 0.0.0.0:$PORT app:app
