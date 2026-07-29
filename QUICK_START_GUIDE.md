# Quick Start Guide - Frontend & Backend Integration

## What Was Fixed

Your frontend was **not calling the backend** because it was using a completely mocked authentication system. We've fixed this and several other issues.

## Issues Resolved

1. ✅ **Database URL** - Changed from `postgresql://` to `postgresql+asyncpg://`
2. ✅ **FastAPI Syntax** - Fixed parameter order in backend routes
3. ✅ **Frontend Auth** - Changed from mock to real API calls
4. ✅ **Environment Config** - Created `.env.local` for frontend
5. ✅ **Token Management** - Added JWT token storage and Authorization headers

---

## Start Your Application

### Terminal 1 - Backend
```bash
cd backend
uvicorn main:app --reload
```
Backend runs at: **http://localhost:8000**

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```
Frontend runs at: **http://localhost:3000**

---

## Test the Connection

### Option 1: Use Test Script
```bash
./test_frontend_backend_connection.sh
```

### Option 2: Manual Test

1. **Open browser**: http://localhost:3000/login

2. **Create a test user** (in Terminal 3):
```bash
cd backend
python create_test_user.py
```

3. **Try to login** with the credentials you created

4. **Check Browser DevTools** → Network tab:
   - You should see `POST /auth/login` request
   - You should see `GET /auth/me` request
   - Both should return JSON data

---

## What Changed in Frontend

### Before (Mock Auth)
```typescript
// frontend/lib/auth.tsx
async function login(email: string, password: string) {
  // ❌ Created fake user without API call
  const fakeUser = { id: 'u-001', name: email, ... };
  localStorage.setItem('gatekeeper_user', JSON.stringify(fakeUser));
}
```

### After (Real Auth)
```typescript
// frontend/lib/auth.tsx
async function login(email: string, password: string) {
  // ✅ Calls real backend API
  await authApi.login(email, password);        // POST /auth/login
  const userData = await authApi.getCurrentUser(); // GET /auth/me
  setUser(userData);
}
```

---

## Authentication Flow

```
┌──────────┐                           ┌──────────┐
│ Frontend │                           │ Backend  │
│ :3000    │                           │ :8000    │
└────┬─────┘                           └────┬─────┘
     │                                      │
     │ 1. POST /auth/login                  │
     │    {email, password}                 │
     ├──────────────────────────────────────>
     │                                      │
     │ 2. JWT token                         │
     │    {access_token: "...", ...}        │
     <──────────────────────────────────────┤
     │                                      │
     │ Store token in localStorage          │
     ├─────────┐                            │
     │         │                            │
     <─────────┘                            │
     │                                      │
     │ 3. GET /auth/me                      │
     │    Authorization: Bearer <token>     │
     ├──────────────────────────────────────>
     │                                      │
     │ 4. User data                         │
     │    {id, email, full_name, role, ...} │
     <──────────────────────────────────────┤
     │                                      │
     │ Redirect to /dashboard               │
     ├─────────┐                            │
     │         │                            │
     <─────────┘                            │
```

---

## Files Modified

### Backend
- `backend/.env` - Database URL updated
- `backend/main.py` - Fixed parameter order
- `workflow/agents/database_agent.py` - Connection string generation
- `workflow/agents/deployment_agent.py` - Docker Compose config

### Frontend
- `frontend/.env.local` - **Created** with API URL
- `frontend/lib/api.ts` - Added real API functions
- `frontend/lib/auth.tsx` - Changed to use real backend
- `frontend/pages/login.tsx` - Better error handling

---

## Verify It's Working

### 1. Backend Health Check
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok"}`

### 2. Frontend API URL
Open DevTools Console on http://localhost:3000 and run:
```javascript
console.log(process.env.NEXT_PUBLIC_API_URL)
```
Expected: `http://localhost:8000`

### 3. Token Storage
After login, check DevTools → Application → Local Storage:
- Should see `auth_token` with JWT value
- Should NOT see `gatekeeper_user` (old mock system)

### 4. Network Requests
Login and check DevTools → Network tab:
- `POST http://localhost:8000/auth/login` - Status 200
- `GET http://localhost:8000/auth/me` - Status 200

---

## Common Issues

### "Account is not approved"
**Cause**: New users need admin approval  
**Fix**: Update database or use admin to approve:
```sql
UPDATE users SET is_approved = true WHERE email = 'your@email.com';
```

### "Invalid email or password"
**Cause**: Wrong credentials or user doesn't exist  
**Fix**: Register first, then login

### CORS Error
**Cause**: Backend not allowing frontend origin  
**Fix**: Already configured! Just ensure backend is running

### "Cannot connect to backend"
**Cause**: Backend not running or wrong URL  
**Fix**: 
1. Start backend: `cd backend && uvicorn main:app --reload`
2. Check frontend/.env.local has correct URL

---

## Environment Variables

### Backend (`backend/.env`)
```env
# Use postgresql+asyncpg:// not postgresql://
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db_name
```

### Frontend (`frontend/.env.local`)
```env
# Must start with NEXT_PUBLIC_ to be available in browser
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Next Steps

1. ✅ **Authentication works** - Frontend now calls backend
2. 🔄 **Dashboard integration** - Replace hardcoded data with API calls
3. 🔄 **Visitor management** - Connect create/approve/reject actions to backend
4. 🔄 **Testing** - Fix Testing Agent to generate proper backend tests

---

## Need Help?

Check these files for details:
- `COMPLETE_FIX_SUMMARY_FINAL.md` - Detailed technical changes
- `FRONTEND_BACKEND_CONNECTION_FIXES.md` - Original issue analysis
- `test_frontend_backend_connection.sh` - Automated testing script

Run the test script to verify everything:
```bash
./test_frontend_backend_connection.sh
```

---

## Success! 🎉

Your frontend is now **properly connected** to your backend. Login requests go to the real API at localhost:8000, JWT tokens are stored and used for authenticated requests, and you have a real authentication flow.
