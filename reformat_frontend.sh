#!/bin/bash

# Script to reformat minified frontend files using Prettier

cd /Users/chowdaryadithyasai/Documents/visitor_workflow/frontend

echo "Installing Prettier..."
npm install --save-dev --silent prettier 2>&1 | grep -v "npm warn"

echo ""
echo "Reformatting all TypeScript/React files..."
npx prettier --write "**/*.{ts,tsx,js,jsx}" --loglevel error

echo ""
echo "✅ All files reformatted!"
echo ""
echo "Running build to verify..."
npm run build
