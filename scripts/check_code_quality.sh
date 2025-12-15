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

# 4. 运行测试
echo "Running tests..."
pytest tests/ -v --cov=src/holoassist --cov-report=term-missing

# 5. 检查覆盖率
coverage_threshold=80
coverage=$(pytest tests/ --cov=src/holoassist --cov-report=term | grep TOTAL | awk '{print $NF}' | sed 's/%//')
if (( $(echo "$coverage < $coverage_threshold" | bc -l) )); then
    echo "Coverage $coverage% is below threshold $coverage_threshold%"
    exit 1
fi

echo "All checks passed!"
