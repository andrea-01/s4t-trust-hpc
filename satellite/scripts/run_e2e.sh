#!/bin/bash
echo "1. Lease worker-4"
curl -s -X POST http://localhost:8000/leasing/lease -H "Content-Type: application/json" -d '{"device_id":"worker-4"}'

echo -e "\n\n2. Lease 2 nodes from satellite"
res=$(curl -s -X POST http://localhost:8001/pipeline/lease -H "Content-Type: application/json" -d '{"count":2}')
echo $res
pip_id=$(echo $res | grep -o '"pipeline_id":"[^"]*' | cut -d'"' -f4)
echo "Pipeline ID: $pip_id"

echo -e "\n\n3. Gateway status worker-1"
curl -s http://localhost:8000/leasing/status/worker-1

echo -e "\n\n4. Run pipeline"
curl -s -X POST http://localhost:8001/pipeline/$pip_id/run -H "Content-Type: application/json" -d '{"operation":"INCREMENT_COUNTER","initial_value":10}'

echo -e "\n\n5. Release pipeline"
curl -s -X POST http://localhost:8001/pipeline/$pip_id/release

echo -e "\n\n6. Gateway status worker-1 after release"
curl -s http://localhost:8000/leasing/status/worker-1
