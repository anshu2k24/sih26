---
title: eRTMAC NWIS AI Engine
emoji: 🛢️
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
---

# eRTMAC-NWIS AI & OCR Inference Engine
Dedicated containerized AI microservice for SIH 2026 PS121.

## Capabilities
* **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense semantic vectors).
* **Handwritten OCR**: `microsoft/trocr-base-handwritten` or Vision-Language OCR pipeline for field tour sheets.
* **REST API**: High-throughput FastAPI endpoints designed to be invoked by the Render backend.

## Endpoints
* `GET /`: Service metadata.
* `GET /health`: Health probe.
* `POST /embed`: Batch embedding generation.
* `POST /ocr`: Handwritten tour sheet text extraction.
