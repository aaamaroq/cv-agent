FROM node:24-alpine AS frontend-build

WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY docs/ ./docs/
COPY profiles/ ./profiles/
COPY --from=frontend-build /web/dist ./web/dist

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn cv_chat.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
