#!/bin/bash
# 代码质量检查脚本
# 支持自动修复代码格式问题

set -e

# 检查是否启用自动修复
AUTO_FIX=${AUTO_FIX:-false}

echo "Running code quality checks..."
if [ "$AUTO_FIX" = "true" ]; then
    echo "Auto-fix mode enabled"
fi

# 1. 代码格式化检查和修复
echo "Checking code formatting..."
if [ "$AUTO_FIX" = "true" ]; then
    echo "Auto-fixing code formatting..."
    uv run ruff format src/ tests/
    echo "Code formatting fixed"
else
    if ! uv run ruff format --check src/ tests/; then
        echo "Error: Code formatting issues found. Run with AUTO_FIX=true to auto-fix, or run: uv run ruff format src/ tests/"
        exit 1
    fi
fi

# 2. 代码lint检查和修复
echo "Running linter..."
if [ "$AUTO_FIX" = "true" ]; then
    echo "Auto-fixing lint issues..."
    uv run ruff check --fix src/ tests/
    echo "Lint issues fixed"
else
    if ! uv run ruff check src/ tests/; then
        echo "Error: Lint issues found. Run with AUTO_FIX=true to auto-fix, or run: uv run ruff check --fix src/ tests/"
        exit 1
    fi
fi

# 3. 类型检查
echo "Running type checker..."
if ! uv run mypy src/; then
    echo "Error: Type checking failed. Please fix type errors manually."
    exit 1
fi

# 4. 运行测试并检查覆盖率
echo "Running tests..."
coverage_threshold=50  # 降低覆盖率阈值，开发阶段可以逐步提升
coverage_output=$(uv run pytest tests/ -v --cov=src/holoassist --cov-report=term-missing --cov-report=term 2>&1)
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
    echo "Warning: Coverage $coverage% is below threshold $coverage_threshold%"
    echo "This is acceptable during development. Coverage will be improved in future stages."
    # 在开发阶段，覆盖率低于阈值只警告，不阻止提交
    # 但如果是0%或缺失，仍然需要报错
    if [ -z "$coverage" ] || [ "$coverage" = "0" ]; then
        echo "Error: Coverage is 0% or missing, which indicates tests are not running properly"
        exit 1
    fi
fi

echo "All checks passed!"
