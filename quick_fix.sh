#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║          Quick Fix - Get Your Frontend/Backend Working       ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if backend is running
echo "Checking backend..."
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on http://127.0.0.1:8000"
else
    echo "❌ Backend is NOT running"
    echo ""
    echo "To start backend:"
    echo "  cd backend"
    echo "  pip3 install -r requirements.txt"
    echo "  uvicorn main:app --reload"
    echo ""
fi

# Check if frontend dependencies are installed
echo ""
echo "Checking frontend..."
if [ -d "frontend/node_modules" ]; then
    echo "✅ Frontend dependencies installed"
else
    echo "⚠️  Frontend dependencies not installed"
    echo "Installing now..."
    cd frontend && npm install && cd ..
fi

# Check if frontend is running
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is running on http://localhost:3000"
else
    echo "❌ Frontend is NOT running"
    echo ""
    echo "To start frontend:"
    echo "  cd frontend"
    echo "  npm run dev"
    echo ""
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                     RECOMMENDATION                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Your current frontend was generated BEFORE the fixes."
echo "For best results:"
echo ""
echo "1. Backup current work (if needed)"
echo "2. Delete generated code:"
echo "   rm -rf frontend backend"
echo ""
echo "3. Run workflow again:"
echo "   python3 main.py Visitor_Management_Application_Requirements_Specification.md"
echo ""
echo "The new generation will have:"
echo "  ✅ Properly formatted code"
echo "  ✅ Auto-installed dependencies"  
echo "  ✅ Matching types"
echo "  ✅ Code-specific tests"
echo ""
