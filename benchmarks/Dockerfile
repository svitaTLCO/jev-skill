FROM python:3.11-alpine

RUN apk add --no-cache docker-cli

WORKDIR /workspace
COPY scripts /workspace/scripts
COPY benchmarks/evaluation_manifest.json /workspace/benchmarks/evaluation_manifest.json
ENTRYPOINT []
