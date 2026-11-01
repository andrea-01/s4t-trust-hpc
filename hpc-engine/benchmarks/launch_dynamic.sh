#!/usr/bin/env bash
set -euo pipefail

# launch_dynamic.sh - Launch dynamic master-worker MPI benchmark with explicit binding
# Master rank 0 dynamically assigns chunks to workers.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export HWLOC_COMPONENTS="${HWLOC_COMPONENTS:--gl}"

# Arguments:
# $1: ranks (default: 3, meaning 1 master + 2 workers)
# $2: chunk_size (default: 50)
# $3: threads per worker (default: 2)
# $4: batch_size (default: 5000)
# $5: csv_out (default: hpc-engine/results/m13/results_mpi_dynamic.csv)
# $6: optional flag --pcores (bind to logical CPUs 0-11)
RANKS="${1:-3}"
CHUNK_SIZE="${2:-50}"
THREADS="${3:-2}"
BATCH_SIZE="${4:-5000}"
CSV_OUT="${5:-${REPO_ROOT}/hpc-engine/results/m13/results_mpi_dynamic.csv}"

USE_PCORES=0
for arg in "$@"; do
    if [ "$arg" = "--pcores" ]; then
        USE_PCORES=1
    fi
done

# Locate binary
BIN=""
if [ -f "${REPO_ROOT}/build/hpc_engine_mpi_dynamic" ]; then
    BIN="${REPO_ROOT}/build/hpc_engine_mpi_dynamic"
elif [ -f "${REPO_ROOT}/hpc-engine/build/hpc_engine_mpi_dynamic" ]; then
    BIN="${REPO_ROOT}/hpc-engine/build/hpc_engine_mpi_dynamic"
else
    echo "Error: Binary hpc_engine_mpi_dynamic not found in build/ or hpc-engine/build/."
    echo "Please build the project first."
    exit 1
fi

mkdir -p "$(dirname "${CSV_OUT}")"

echo "=========================================================="
echo " HPC Benchmark Launch: Dynamic MPI Master-Worker"
echo "=========================================================="
echo "Date: $(date -Iseconds)"
echo "Host: $(hostname)"
echo "CPU Governor:"
if [ -d "/sys/devices/system/cpu/cpufreq" ] || [ -f "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" ]; then
    cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null | sort | uniq -c || echo "  Unable to read governor"
else
    echo "  cpufreq sysfs not available"
fi
echo "Binary: ${BIN}"
echo "Ranks: ${RANKS} (1 Master + $(( RANKS - 1 )) Workers)"
echo "Threads per worker: ${THREADS}"
echo "Chunk Size: ${CHUNK_SIZE}"
echo "Batch Size: ${BATCH_SIZE}"
echo "Output CSV: ${CSV_OUT}"
echo "Binding Policy: --report-bindings --map-by slot:PE=${THREADS} --bind-to core"
if [ "${USE_PCORES}" -eq 1 ]; then
    echo "CPU Mask: taskset -c 0-11 (P-cores only)"
fi
echo "=========================================================="

PREFIX_CMD=""
if [ "${USE_PCORES}" -eq 1 ]; then
    PREFIX_CMD="taskset -c 0-11"
fi

export OMP_NUM_THREADS="${THREADS}"

${PREFIX_CMD} mpirun \
    --report-bindings \
    --map-by "slot:PE=${THREADS}" \
    --bind-to core \
    -np "${RANKS}" \
    "${BIN}" "${BATCH_SIZE}" "${CHUNK_SIZE}" "${THREADS}" "${CSV_OUT}"

echo "Run completed successfully."
