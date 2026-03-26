#!/bin/bash
# Docker build script with registry fallback

# Try to build with --pull flag to force pull from official registry
echo "Building frontend Docker image..."
docker build \
  --pull \
  --platform linux/amd64 \
  -t zhiyiquant-frontend:latest \
  -f Dockerfile \
  .

if [ $? -ne 0 ]; then
  echo "Build failed, trying with no-cache..."
  docker build \
    --no-cache \
    --platform linux/amd64 \
    -t zhiyiquant-frontend:latest \
    -f Dockerfile \
    .
fi
