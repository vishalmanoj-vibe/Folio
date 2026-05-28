#!/bin/bash
# scratch/run_tests.sh
# ====================
# Unified test runner for the portfolio dashboard project.
# Ensures the correct PYTHONPATH is set and triggers pytest-cov coverage metrics.

# Ensure we exit immediately if any command fails
set -e

# Define color tokens for beautiful terminal output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Initialising Portfolio Dashboard Test Runner...${NC}"

# Set the Python Path to the project root
export PYTHONPATH=.

# Detect the best pytest executable to use
if [ -f "venv/bin/pytest" ]; then
    PYTEST_CMD="venv/bin/pytest"
elif [ -f ".venv/bin/pytest" ]; then
    PYTEST_CMD=".venv/bin/pytest"
else
    PYTEST_CMD="pytest"
fi

echo -e "${CYAN}Using pytest executable: ${PYTEST_CMD}${NC}"

# Default behavior: run all tests in scratch/tests/ except the heavy forecasting task by default
# unless specific arguments are passed.
if [ $# -eq 0 ]; then
    echo -e "${CYAN}Running FAST unit tests (skipping heavy ML forecasting to keep cycles instant)...${NC}"
    $PYTEST_CMD scratch/tests/ \
        --ignore=scratch/tests/test_prediction_task.py \
        --cov=services \
        --cov=components \
        --cov=pages \
        --cov=data \
        --cov-report=html
else
    echo -e "${CYAN}Running tests with custom arguments: $@${NC}"
    $PYTEST_CMD scratch/tests/ "$@"
fi

echo -e "${GREEN}✅ Test run completed successfully!${NC}"
echo -e "${GREEN}📊 Coverage HTML report has been generated at: htmlcov/index.html${NC}"
echo -e "To open the report in your browser, run: ${CYAN}open htmlcov/index.html${NC}"
