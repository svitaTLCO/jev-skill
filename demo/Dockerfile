FROM python:3.11-alpine

WORKDIR /app
COPY scripts /app/scripts
COPY demo /app/demo
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8088
CMD ["python", "-m", "scripts.demo_server"]
