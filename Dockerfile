FROM python:3.12-slim

# Keep Python output visible in Docker logs and make the HTTP port configurable.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    PYTHONPATH=/opt/rapidocr-docker/src

WORKDIR /opt/rapidocr-docker

# Runtime libraries are needed by image and OCR dependencies on slim Debian.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Initialize RapidOCR during image build so default model files are present offline.
RUN python -c "from rapidocr import RapidOCR; RapidOCR(); print('RapidOCR initialized')"

COPY src ./src

EXPOSE 8000

ENTRYPOINT ["python", "-m", "rapidocr_offline.entrypoint"]
CMD ["server"]
