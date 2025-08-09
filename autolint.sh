#!/bin/bash
set -e

echo "🐍 Installing linters and formatters"
pip install --quiet flake8 isort autoflake autopep8 docformatter

echo "🧹🗑️  Removing unused imports with autoflake..."
autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r .

echo "📚 Sorting imports with isort..."
isort .

echo "🖌️✨ Formatting docstrings with docformatter (line length 79)..."
docformatter --in-place --wrap-summaries 79 --wrap-descriptions 79 -r .

echo "🖌️✨ Formatting code with autopep8 (line length 99)..."
autopep8 --in-place --aggressive --max-line-length 99 -r .

echo "🔎 Linting with flake8..."
flake8 .

echo "✅✨ All linting and formatting complete!"