FROM python:3.11-alpine

# node is required for GenericRuntimeValidator's Tier-0 mechanical checks
# (compiler-in-the-loop per AGENTS.md): it runs `node -e` against the inner script block.
RUN apk add --no-cache nodejs

WORKDIR /app
COPY scripts /app/scripts
COPY demo /app/demo
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8088
CMD ["python", "-m", "scripts.demo_server"]
