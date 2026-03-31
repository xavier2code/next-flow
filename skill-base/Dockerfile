FROM python:3.12-slim

WORKDIR /

# Install sidecar dependencies
COPY sidecar/sidecar.py /sidecar/sidecar.py
COPY sidecar/requirements.txt /sidecar/requirements.txt
RUN pip install --no-cache-dir -r /sidecar/requirements.txt

# Create non-root user
RUN useradd -m -u 1000 skilluser
RUN chown -R skilluser:skilluser /sidecar

USER 1000:1000

EXPOSE 8080

CMD ["python", "/sidecar/sidecar.py"]
