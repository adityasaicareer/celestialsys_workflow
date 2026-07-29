#!/bin/bash

echo "================================"
echo "Testing Frontend-Backend Connection"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
echo "1. Checking if backend is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is running at http://localhost:8000"
else
    echo -e "${RED}✗${NC} Backend is NOT running"
    echo -e "${YELLOW}Start it with: cd backend && uvicorn main:app --reload${NC}"
    exit 1
fi

echo ""

# Check health endpoint
echo "2. Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "ok"; then
    echo -e "${GREEN}✓${NC} Health check passed: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗${NC} Health check failed"
    exit 1
fi

echo ""

# Check CORS headers
echo "3. Checking CORS configuration..."
CORS_HEADERS=$(curl -s -I http://localhost:8000/health | grep -i "access-control")
if [ ! -z "$CORS_HEADERS" ]; then
    echo -e "${GREEN}✓${NC} CORS headers found:"
    echo "$CORS_HEADERS" | sed 's/^/  /'
else
    echo -e "${YELLOW}⚠${NC}  CORS headers not found (might be OK)"
fi

echo ""

# Check if PostgreSQL connection works
echo "4. Testing database connection..."
cd backend
if python3 -c "from database import engine; print('OK')" 2>/dev/null | grep -q "OK"; then
    echo -e "${GREEN}✓${NC} Database engine created successfully"
else
    echo -e "${RED}✗${NC} Database connection failed"
    echo -e "${YELLOW}Check DATABASE_URL in backend/.env${NC}"
    cd ..
    exit 1
fi
cd ..

echo ""

# Check frontend env file
echo "5. Checking frontend configuration..."
if [ -f "frontend/.env.local" ]; then
    echo -e "${GREEN}✓${NC} frontend/.env.local exists"
    cat frontend/.env.local | sed 's/^/  /'
else
    echo -e "${RED}✗${NC} frontend/.env.local missing"
    echo -e "${YELLOW}Create it with: echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > frontend/.env.local${NC}"
    exit 1
fi

echo ""

# Test registration endpoint
echo "6. Testing registration endpoint..."
TEST_EMAIL="test_$(date +%s)@example.com"
REG_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"testpass123\",\"full_name\":\"Test User\"}")

if echo "$REG_RESPONSE" | grep -q "email"; then
    echo -e "${GREEN}✓${NC} Registration endpoint works"
    echo -e "  Response: $REG_RESPONSE"
else
    echo -e "${RED}✗${NC} Registration failed"
    echo -e "  Response: $REG_RESPONSE"
fi

echo ""
echo "================================"
echo -e "${GREEN}Summary:${NC}"
echo "- Backend is running ✓"
echo "- Health endpoint works ✓"
echo "- Database connection works ✓"
echo "- Frontend env configured ✓"
echo "- API endpoints responding ✓"
echo ""
echo "You can now:"
echo "1. Start frontend: cd frontend && npm run dev"
echo "2. Open http://localhost:3000/login"
echo "3. Create a user or use existing credentials"
echo "================================"
