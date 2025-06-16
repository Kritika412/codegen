#!/bin/bash

echo "Testing FastAPI backend..."

# 서버가 실행 중인지 확인
echo "1. Testing root endpoint:"
curl -s http://localhost:8000/ || echo "Server not running on port 8000"

echo -e "\n\n2. Testing sprints endpoint:"
curl -s http://localhost:8000/api/sprints || echo "Sprints endpoint failed"

echo -e "\n\n3. Testing issues endpoint:"
curl -s http://localhost:8000/api/issues || echo "Issues endpoint failed"

echo -e "\n\nDone!"
