#!/bin/bash
cd "$(dirname "$0")"
docker build -t anyburl:java11 .
