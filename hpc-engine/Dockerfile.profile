FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libssl-dev \
    valgrind \
    ubuntu-dbgsym-keyring \
    && echo 'deb [signed-by=/usr/share/keyrings/ubuntu-dbgsym-keyring.gpg] http://ddebs.ubuntu.com noble main restricted universe multiverse' > /etc/apt/sources.list.d/ddebs.list \
    && echo 'deb [signed-by=/usr/share/keyrings/ubuntu-dbgsym-keyring.gpg] http://ddebs.ubuntu.com noble-updates main restricted universe multiverse' >> /etc/apt/sources.list.d/ddebs.list \
    && apt-get update \
    && apt-get install -y libssl3t64-dbgsym \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Build with -O2 -g for full debug symbol resolution
RUN g++ -O2 -g -fopenmp -std=c++17 -I src/onboarding \
    src/onboarding/main.cpp \
    src/onboarding/device_generator.cpp \
    src/onboarding/signature_bench.cpp \
    src/onboarding/csv_writer.cpp \
    -lssl -lcrypto -o /app/hpc_engine_bench_profile

ENTRYPOINT ["/bin/bash"]
