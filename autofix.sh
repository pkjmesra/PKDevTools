#!/bin/bash

rm -rf build
rm -rf dist

# Run isort excluding the specific file
isort . --skip PKDevTools/classes/__init__.py

# Run ruff format excluding the specific file  
ruff format . --exclude PKDevTools/classes/__init__.py

# Get flake8 statistics and extract unique error codes
ERROR_CODES=$(flake8 . --count --exit-zero --max-complexity=25 --max-line-length=180 --statistics | \
               grep -oE '[A-Z][0-9]+' | \
               sort -u)

# Convert error codes to autopep8 format (comma-separated list)
SELECT_CODES=$(echo "$ERROR_CODES" | tr '\n' ',' | sed 's/,$//')

if [ -z "$SELECT_CODES" ]; then
    echo "No flake8 errors found to fix."
    exit 0
fi

echo "Fixing the following flake8 error codes: $SELECT_CODES"

# Run autopep8 on all Python files for the specific error codes, excluding pkbrokers/kite/__init__.py
find . -name "*.py" -not -path "./PKDevTools/classes/__init__.py" -print0 | while IFS= read -r -d '' file; do
    autopep8 --in-place --select="$SELECT_CODES" --aggressive "$file"
done

# Also exclude the file from flake8 statistics if needed
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=180 --statistics --exclude=pkbrokers/kite/__init__.py

echo "Autopep8 fixes completed for codes: $SELECT_CODES"
