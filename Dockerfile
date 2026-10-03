FROM python:3.12-slim
WORKDIR /app
COPY engine.py server.py auth.py serve_private.py ./
COPY static ./static
ENV PORT=8080 PYTHONUNBUFFERED=1 DATA_DIR=/app/data COOKIE_SECURE=1
EXPOSE 8080
CMD ["python", "serve_private.py"]
