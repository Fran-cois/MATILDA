#!/bin/bash
# Complete benchmark workflow: Run benchmark + Generate comparison

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
RUNS=5
EXPERIMENT_NAME="benchmark_$(date +%Y%m%d_%H%M%S)"
ALGORITHMS="MATILDA SPIDER ANYBURL POPPER AMIE3"
DATASETS="Bupa BupaImperfect ComparisonDataset ImperfectTest"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --runs)
            RUNS="$2"
            shift 2
            ;;
        --experiment-name)
            EXPERIMENT_NAME="$2"
            shift 2
            ;;
        --algorithms)
            ALGORITHMS="$2"
            shift 2
            ;;
        --datasets)
            DATASETS="$2"
            shift 2
            ;;
        --quick)
            RUNS=2
            ALGORITHMS="MATILDA SPIDER"
            DATASETS="Bupa"
            echo -e "${YELLOW}⚡ Quick mode: 2 runs, MATILDA+SPIDER, Bupa only${NC}"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --runs N                  Number of runs per algorithm-dataset (default: 5)"
            echo "  --experiment-name NAME    Experiment name (default: benchmark_TIMESTAMP)"
            echo "  --algorithms \"A1 A2...\"   Algorithms to test (default: all)"
            echo "  --datasets \"D1 D2...\"     Datasets to test (default: all)"
            echo "  --quick                   Quick test: 2 runs, MATILDA+SPIDER, Bupa only"
            echo "  --help                    Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --quick                          # Quick test"
            echo "  $0 --runs 10                        # Full benchmark with 10 runs"
            echo "  $0 --algorithms \"MATILDA SPIDER\"   # Only MATILDA vs SPIDER"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MATILDA Complete Benchmark Workflow         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Runs per combination: $RUNS"
echo "  Experiment name: $EXPERIMENT_NAME"
echo "  Algorithms: $ALGORITHMS"
echo "  Datasets: $DATASETS"
echo ""

# Step 1: Run benchmark
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}STEP 1/2: Running Benchmark${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

python3 run_full_benchmark.py \
    --runs "$RUNS" \
    --experiment-name "$EXPERIMENT_NAME" \
    --algorithms $ALGORITHMS \
    --datasets $DATASETS

BENCHMARK_EXIT=$?

if [ $BENCHMARK_EXIT -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Benchmark completed with errors (exit code: $BENCHMARK_EXIT)${NC}"
    echo "Continuing to comparison step..."
else
    echo -e "${GREEN}✅ Benchmark completed successfully${NC}"
fi

echo ""

# Step 2: Generate comparison
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}STEP 2/2: Generating Comparison Report${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

python3 compare_matilda_benchmark.py

COMPARISON_EXIT=$?

if [ $COMPARISON_EXIT -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Comparison generation failed (exit code: $COMPARISON_EXIT)${NC}"
    exit $COMPARISON_EXIT
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Complete Workflow Finished!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Find the experiment directory
EXP_DIR=$(ls -td data/output/mlruns/*/ | head -1)

if [ -n "$EXP_DIR" ]; then
    echo -e "${GREEN}📂 Results Location:${NC}"
    echo "   $EXP_DIR"
    echo ""
    echo -e "${GREEN}📄 Generated Files:${NC}"
    
    if [ -f "${EXP_DIR}MATILDA_COMPARISON_REPORT.md" ]; then
        echo "   ✓ Markdown Report:  ${EXP_DIR}MATILDA_COMPARISON_REPORT.md"
    fi
    
    if [ -f "${EXP_DIR}matilda_comparison_table.tex" ]; then
        echo "   ✓ LaTeX Table:      ${EXP_DIR}matilda_comparison_table.tex"
    fi
    
    if [ -f "${EXP_DIR}matilda_comparison_data.json" ]; then
        echo "   ✓ JSON Data:        ${EXP_DIR}matilda_comparison_data.json"
    fi
    
    if [ -f "${EXP_DIR}benchmark_table_*.tex" ]; then
        echo "   ✓ Benchmark Table:  ${EXP_DIR}benchmark_table_*.tex"
    fi
    
    echo ""
    echo -e "${GREEN}📊 Quick View:${NC}"
    echo "   cat ${EXP_DIR}MATILDA_COMPARISON_REPORT.md"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
