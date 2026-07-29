# Frontend-Backend Connection Fixes

## Issues Found

### 1. **Mock Authentication System**
**Problem**: The frontend auth system (`frontend/lib/auth.tsx`) doesn't call the backend at all. It creates fake user objects locally.

**Current Code**:
```typescript
async function login(email: string, _password: string) {
  // Creates fake user without API call
  const nextUser: AuthUser = {
    id: 'u-001',
    name: email.split('@')[0].replace('.', ' '),
    email,
    role: email.includes('admin') ? 'SUPER_ADMIN' : 'APPROVER',
    location: 'All locations'
  };
  // ...stores in localStorage
}
```

**Needed**: Real API call to `POST /auth/login` endpoint

### 2. **Missing Environment File**
**Problem**: Frontend has no `.env.local` file to configure API URL

**Fix**: Create `frontend/.env.local` with:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. **Hardcoded Dashboard Data**
**Problem**: Dashboard uses static data instead of fetching from backend

**Location**: `frontend/pages/dashboard.tsx`

### 4. **Backend Issues Fixed**
✅ Database URL updated to use `postgresql+asyncpg://` for async driver
✅ CORS configured for localhost:3000
✅ FastAPI parameter order fixed (filters before format)

## Next Steps

1. **Update auth.tsx** to call real backend endpoints:
   - POST /auth/login
   - POST /auth/register  
   - GET /auth/me
   
2. **Create .env.local** file in frontend

3. **Update dashboard** to fetch real data from backend

4. **Add token management** for authenticated requests
