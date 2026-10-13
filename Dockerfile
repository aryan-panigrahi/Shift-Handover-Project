# Shift Handover Briefing - Container Deployment
# AMD Developer Hackathon - Intelligent Industry Track

FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/
COPY tests/ ./tests/
COPY README.md PRD.md TECHNICAL_DESIGN.md DATA_MODEL_AND_API.md MVP_PLAN.md DEMO_AND_PITCH.md RISKS_AND_EVALUATION.md DECISIONS.md ./

# Environment defaults
ENV PORT=8000
ENV HOST=0.0.0.0
ENV DATABASE_PATH=/app/app/data/shift_handover.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
