FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libssl-dev \
    pkg-config \
    protobuf-compiler \
    protobuf-compiler-grpc \
    libgrpc++-dev \
    openmpi-bin \
    libopenmpi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

# Compile pipeline worker and mpi experiment
RUN mkdir -p build && cd build && cmake ../hpc-engine && make pipeline_worker hpc_engine_mpi

ENV PORT=50051
EXPOSE 50051

ENTRYPOINT ["./build/pipeline_worker"]
