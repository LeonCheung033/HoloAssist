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
coverage=$(echo "$coverage_output" | grep TOTAL | awk '{print $NF}' | sed 's/%//' || echo "")

# 检查是否有测试文件
test_files=$(find tests/ -name "test_*.py" -type f 2>/dev/null | wc -l | tr -d ' ')

# 处理覆盖率缺失或为0%的情况
if [ -z "$coverage" ] || [ "$coverage" = "" ] || [ "$coverage" = "0" ]; then
    if [ "$test_files" -eq 0 ]; then
        echo "Warning: No coverage data found or coverage is 0%, and no test files exist"
        echo "This is expected during initial project setup"
        echo "Coverage check skipped - please add tests in future stages"
        exit 0
    else
        echo "Error: Test files exist but coverage is 0% or missing"
        echo "This indicates tests are not being executed or are not covering any code"
        exit 1
    fi
fi

# 使用Python进行可靠的浮点数比较（不依赖bc）
if ! python3 -c "import sys; sys.exit(0 if float('$coverage') >= float('$coverage_threshold') else 1)" 2>/dev/null; then
    echo "Coverage $coverage% is below threshold $coverage_threshold%"
    exit 1
fi

echo "All checks passed!"
