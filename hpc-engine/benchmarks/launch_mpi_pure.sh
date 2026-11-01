#!/usr/bin/env bash
set -euo pipefail

# launch_mpi_pure.sh - Launch pure MPI benchmark with explicit core binding
# Binding policy: --bind-to core

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export HWLOC_COMPONENTS="${HWLOC_COMPONENTS:--gl}"

# Arguments:
# $1: ranks (default: 4)
# $2: batch_size (default: 5000)
# $3: csv_out (default: hpc-engine/results/m13/results_mpi_pure.csv)
# $4: optional flag --pcores (bind to logical CPUs 0-11)
RANKS="${1:-4}"
BATCH_SIZE="${2:-5000}"
CSV_OUT="${3:-${REPO_ROOT}/hpc-engine/results/m13/results_mpi_pure.csv}"
PCORES_FLAG="${4:-}"

# Check for --pcores flag in any argument
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
echo " HPC Benchmark Launch: Pure MPI"
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
echo "Threads per rank: 1"
echo "Batch Size: ${BATCH_SIZE}"
echo "Output CSV: ${CSV_OUT}"
echo "Binding Policy: --report-bindings --bind-to core"
if [ "${USE_PCORES}" -eq 1 ]; then
    echo "CPU Mask: taskset -c 0-11 (P-cores only)"
fi
echo "=========================================================="

PREFIX_CMD=""
if [ "${USE_PCORES}" -eq 1 ]; then
    PREFIX_CMD="taskset -c 0-11"
fi

${PREFIX_CMD} mpirun \
    --use-hwthread-cpus \
    --report-bindings \
    --bind-to core \
    -np "${RANKS}" \
    "${BIN}" "${BATCH_SIZE}" 1 "${CSV_OUT}"

echo "Run completed successfully."
