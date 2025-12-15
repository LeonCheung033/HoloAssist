#!/bin/bash
# 使用uv管理依赖

echo "Syncing dependencies with uv..."
uv sync

echo "Checking dependency tree..."
uv tree

echo "Checking for conflicts..."
uv pip check
