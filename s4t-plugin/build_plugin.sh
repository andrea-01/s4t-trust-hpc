#!/bin/bash
set -e

# Go to the script directory
cd "$(dirname "$0")"

echo "Building S4T plugin bundle..."

# Clean up previous build
rm -rf build plugin_bundle.py
mkdir -p build/stubs

# Generate gRPC stubs from proto using the satellite container
echo "Generating gRPC stubs..."
# Copy proto to a temporary location inside container
docker exec deploy-satellite-1 mkdir -p /tmp/proto_build
docker cp ../proto/pipeline.proto deploy-satellite-1:/tmp/proto_build/
# Run grpc_tools.protoc inside container
docker exec deploy-satellite-1 python -m grpc_tools.protoc -I/tmp/proto_build --python_out=/tmp/proto_build --grpc_python_out=/tmp/proto_build /tmp/proto_build/pipeline.proto
# Copy generated files back
docker cp deploy-satellite-1:/tmp/proto_build/pipeline_pb2.py build/stubs/
docker cp deploy-satellite-1:/tmp/proto_build/pipeline_pb2_grpc.py build/stubs/

# Patch grpc code for python 3.7 compatibility (grpcio 1.62.x)
sed -i 's/_registered_method=True//g' build/stubs/pipeline_pb2_grpc.py
sed -i '/server.add_registered_method_handlers/d' build/stubs/pipeline_pb2_grpc.py

# Create zip of stubs
echo "Zipping stubs..."
cd build/stubs
zip -q -r ../stubs.zip .
cd ../..

# Encode zip to base64 (ensure no newlines)
echo "Encoding zip..."
BASE64_ZIP=$(base64 -w 0 build/stubs.zip)

# Replace placeholder in template and output to bundle
echo "Injecting into template..."
sed "s|###STUBS_ZIP_BASE64###|$BASE64_ZIP|" plugin_template.py > plugin_bundle.py

echo "Done! Generated plugin_bundle.py"
