#!/bin/bash
# Build Docker image for SPIDER/Metanome

cd "$(dirname "$0")"
docker build -t matilda-spider:latest .
echo "Docker image 'matilda-spider:latest' built successfully"
