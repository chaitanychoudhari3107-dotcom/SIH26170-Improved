# Multi-stage Docker build for SIH26170 Semiconductor Reliability Application

# Stage 1: Build React 19 Frontend
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python FastAPI Backend
FROM python:3.12-slim
WORKDIR /app

# Install Python production dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application, frozen datasets, and compiled frontend assets
COPY backend/ ./backend/
COPY data/ ./data/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Default port for container platforms (Render dynamically sets $PORT)
ENV PORT=8000
EXPOSE 8000

# Start Uvicorn serving both REST API and compiled React SPA
CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
