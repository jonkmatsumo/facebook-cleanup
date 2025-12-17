#!/bin/bash
# Verification script for code quality tools setup
# Run this after installing dependencies: pip install -r requirements-dev.txt

set -e

echo "========================================="
echo "Code Quality Tools Verification"
echo "========================================="
echo ""

# Check if tools are installed
echo "1. Checking if tools are installed..."
if command -v ruff &> /dev/null; then
    echo "   ✓ Ruff is installed"
    ruff --version
else
    echo "   ✗ Ruff is not installed"
    echo "   Install with: pip install ruff"
    exit 1
fi

if command -v mypy &> /dev/null; then
    echo "   ✓ MyPy is installed"
    mypy --version
else
    echo "   ✗ MyPy is not installed"
    echo "   Install with: pip install mypy"
    exit 1
fi

if python3 -c "import pytest_cov" 2>/dev/null; then
    echo "   ✓ pytest-cov is installed"
else
    echo "   ✗ pytest-cov is not installed"
    echo "   Install with: pip install pytest-cov"
    exit 1
fi

echo ""
echo "2. Testing Ruff configuration..."
if ruff check src/ --config .ruff.toml; then
    echo "   ✓ Ruff linting works"
else
    echo "   ⚠ Ruff found issues (this is expected initially)"
fi

if ruff format --check src/ --config .ruff.toml; then
    echo "   ✓ Ruff formatting check works"
else
    echo "   ⚠ Ruff formatting found issues (this is expected initially)"
fi

echo ""
echo "3. Testing MyPy configuration..."
if mypy src/ --config-file mypy.ini; then
    echo "   ✓ MyPy type checking works"
else
    echo "   ⚠ MyPy found type issues (this is expected initially)"
fi

echo ""
echo "4. Testing Coverage configuration..."
if pytest --cov=src --cov-report=term --cov-report=html -q tests/ 2>/dev/null; then
    echo "   ✓ Coverage reporting works"
    if [ -d "htmlcov" ]; then
        echo "   ✓ Coverage HTML report generated in htmlcov/"
    fi
else
    echo "   ⚠ Coverage test failed (may need tests to be runnable)"
fi

echo ""
echo "========================================="
echo "Verification complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  - Fix any linting issues: ruff check src/ --fix"
echo "  - Format code: ruff format src/"
echo "  - Address type issues: mypy src/"
echo "  - Run tests with coverage: pytest --cov=src --cov-report=html"

