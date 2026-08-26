# Manrova - Cloud Run deployment image
# Build context must be the repo root (Manrova/), not this folder, since it
# needs core/, agents/, conductor/ alongside providers/google/adk/.
#
# Build:  docker build -f providers/google/adk/Dockerfile -t manrova .
# Deploy: gcloud run deploy manrova --image <image> --region us-central1

FROM python:3.12-slim

WORKDIR /app

COPY providers/google/adk/requirements-google.txt ./requirements-google.txt
RUN pip install --no-cache-dir -r requirements-google.txt

COPY core/ ./core/
COPY agents/ ./agents/
COPY conductor/ ./conductor/
COPY data/ ./data/
COPY providers/google/adk/ ./providers/google/adk/

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "providers.google.adk.main:app", "--host", "0.0.0.0", "--port", "8080"]
