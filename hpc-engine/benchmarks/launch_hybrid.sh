#!/usr/bin/env bash
set -euo pipefail

# launch_hybrid.sh - Launch hybrid MPI+OpenMP benchmark with explicit thread binding
# Binding policy: --map-by slot:PE=T --bind-to core

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export HWLOC_COMPONENTS="${HWLOC_COMPONENTS:--gl}"

# Arguments:
# $1: ranks (default: 2)
# $2: threads (default: 2)
# $3: batch_size (default: 5000)
# $4: csv_out (default: hpc-engine/results/m13/results_hybrid_mpi_omp.csv)
# $5: optional flag --pcores (bind to logical CPUs 0-11)
RANKS="${1:-2}"
THREADS="${2:-2}"
BATCH_SIZE="${3:-5000}"
CSV_OUT="${4:-${REPO_ROOT}/hpc-engine/results/m13/results_hybrid_mpi_omp.csv}"

USE_PCORES=0
for arg in "$@"; do
    if [ "$arg" = "--pcores" ]; then
        USE_PCORES=1
    fi
done

# Locate binary
BIN=""
if [ -f "${REPO_ROOT}/build/hpc_engine_mpi" ]; then
    BIN="${REPO_ROOT}/build/hpc_engine_mpi"
elif [ -f "${REPO_ROOT}/hpc-engine/build/hpc_engine_mpi" ]; then
    BIN="${REPO_ROOT}/hpc-engine/build/hpc_engine_mpi"
else
    echo "Error: Binary hpc_engine_mpi not found in build/ or hpc-engine/build/."
    echo "Please build the project first."
    exit 1
fi

mkdir -p "$(dirname "${CSV_OUT}")"

echo "=========================================================="
echo " HPC Benchmark Launch: Hybrid MPI + OpenMP"
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
echo "Ranks: ${RANKS}"
echo "Threads per rank: ${THREADS}"
echo "Effective Parallelism: $(( RANKS * THREADS ))"
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
    --use-hwthread-cpus \
    --report-bindings \
    --map-by "slot:PE=${THREADS}" \
    --bind-to hwthread \
    -np "${RANKS}" \
    "${BIN}" "${BATCH_SIZE}" "${THREADS}" "${CSV_OUT}"

echo "Run completed successfully."
