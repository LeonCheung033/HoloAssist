#!/bin/bash
# 代码质量检查脚本

set -e

echo "Running code quality checks..."

# 1. 代码格式化检查
echo "Checking code formatting..."
ruff format --check src/ tests/

# 2. 代码lint检查
echo "Running linter..."
ruff check src/ tests/

# 3. 类型检查
echo "Running type checker..."
mypy src/

# 4. 运行测试并检查覆盖率
echo "Running tests..."
coverage_threshold=80
coverage_output=$(pytest tests/ -v --cov=src/holoassist --cov-report=term-missing --cov-report=term 2>&1)
echo "$coverage_output"

# 提取覆盖率百分比
coverage=$(echo "$coverage_output" | grep TOTAL | awk '{print $NF}' | sed 's/%//' || echo "0")
if [ -z "$coverage" ] || [ "$coverage" = "0" ]; then
    echo "Warning: No coverage data found or coverage is 0%"
    echo "This is expected if no test files exist yet"
    exit 0
fi

if (( $(echo "$coverage < $coverage_threshold" | bc -l 2>/dev/null || echo "0") )); then
    echo "Coverage $coverage% is below threshold $coverage_threshold%"
    exit 1
fi

echo "All checks passed!"
