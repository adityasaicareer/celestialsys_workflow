# Todo Application Requirements

## Project Overview

Build a simple yet functional todo list application with user authentication. The application should allow users to create accounts, log in, and manage their personal todo items with basic CRUD operations.

## Target Users

- Individual users who need a simple task management tool
- Users who want to track their daily tasks and mark them as complete
- Users who need basic account security

## Functional Requirements

### 1. User Authentication

**User Registration:**
- Users can create an account with email and password
- Email must be unique and valid format
- Password must be at least 8 characters long
- Passwords should be hashed before storage
- Display appropriate error messages for validation failures

**User Login:**
- Users can log in with email and password
- Invalid credentials should return clear error messages
- Successful login should return an authentication token (JWT)
- Token should expire after 24 hours

**User Logout:**
- Users can log out, invalidating their session
- Frontend should clear stored authentication tokens

### 2. Todo Management

**Create Todo:**
- Authenticated users can create new todo items
- Each todo has:
  - Title (required, max 200 characters)
  - Description (optional, max 1000 characters)
  - Status (default: pending)
  - Created timestamp (auto-generated)
  - Updated timestamp (auto-generated)
- Todos are associated with the user who created them

**View Todos:**
- Users can view all their own todo items
- Todos should be displayed in reverse chronological order (newest first)
- Show todo title, description, status, and timestamps
- Support filtering by status (all, pending, completed)

**Update Todo:**
- Users can update their own todo items
- Editable fields: title, description, status
- Cannot edit todos belonging to other users
- Update timestamp should be refreshed automatically

**Delete Todo:**
- Users can delete their own todo items
- Cannot delete todos belonging to other users
- Deletion should be permanent (no soft delete)
- Show confirmation before deleting

**Mark as Complete:**
- Users can toggle todo status between "pending" and "completed"
- Visual indicator for completed todos (e.g., strikethrough, checkmark)

## Technical Requirements

### Backend (FastAPI)

**Framework:**
- FastAPI for REST API
- Python 3.11+
- Pydantic for data validation

**Database:**
- PostgreSQL for data storage
- SQLAlchemy ORM for database operations
- Two tables: users, todos

**API Endpoints:**

Authentication endpoints:
```
POST /auth/register - Create new user account
POST /auth/login - Authenticate user
POST /auth/logout - End user session
```

Todo endpoints (all require authentication):
```
GET /todos - List all user's todos (with optional status filter)
POST /todos - Create new todo
GET /todos/{id} - Get specific todo
PUT /todos/{id} - Update todo
DELETE /todos/{id} - Delete todo
PATCH /todos/{id}/complete - Toggle completion status
```

**Security:**
- Password hashing using bcrypt
- JWT token authentication
- Protected routes require valid JWT token
- Users can only access their own todos

**Error Handling:**
- 400 for validation errors
- 401 for authentication errors
- 403 for authorization errors
- 404 for not found
- 500 for server errors

### Frontend (Next.js)

**Framework:**
- Next.js 14+ with App Router
- React 18+
- TypeScript

**Pages:**
1. **Login Page** (`/login`)
   - Email and password input fields
   - "Login" button
   - Link to registration page
   - Display error messages

2. **Registration Page** (`/register`)
   - Email, password, confirm password fields
   - "Register" button
   - Link to login page
   - Display error and validation messages

3. **Dashboard Page** (`/dashboard`) - Protected route
   - Display list of todos
   - Filter buttons (All, Pending, Completed)
   - "Add Todo" button
   - Each todo shows:
     - Title and description
     - Completion checkbox
     - Edit and delete buttons
     - Timestamps
   - Logout button in header

4. **Add/Edit Todo Modal**
   - Title input field
   - Description textarea
   - Save and cancel buttons
   - Form validation

**UI/UX Requirements:**
- Clean, minimal design
- Responsive layout (mobile, tablet, desktop)
- Loading states during API calls
- Success/error toast notifications
- Confirm dialogs for destructive actions
- Accessible (WCAG AA compliance)

**State Management:**
- React Context or simple state management
- Persist JWT token in localStorage
- Clear token on logout

### Database Schema

**Users Table:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Todos Table:**
```sql
CREATE TABLE todos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Non-Functional Requirements

**Performance:**
- API response time < 200ms for most operations
- Frontend should render initial page < 1 second
- Handle at least 100 concurrent users

**Security:**
- All passwords must be hashed
- JWT tokens for authentication
- HTTPS in production (Docker configuration)
- SQL injection prevention (use parameterized queries)
- XSS prevention (input sanitization)

**Reliability:**
- Proper error handling throughout
- Database transactions for data consistency
- Graceful handling of network failures

**Usability:**
- Intuitive user interface
- Clear error messages
- Responsive design for all screen sizes
- Keyboard navigation support

## Deployment Requirements

**Docker Configuration:**
- PostgreSQL container (postgres:15)
- Backend container (FastAPI app)
- Frontend container (Next.js app)
- Docker Compose orchestration
- Environment variables for configuration

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret key for JWT signing
- `API_URL` - Backend API URL for frontend
- `PORT` - Service ports

## Testing Requirements

**Backend Tests:**
- Unit tests for authentication logic
- Unit tests for todo CRUD operations
- Integration tests for API endpoints
- Test coverage > 80%

**Frontend Tests:**
- Component tests for major UI components
- Integration tests for user flows
- Test coverage > 70%

## Success Criteria

The application is considered successful when:
1. Users can register and login successfully
2. Authenticated users can create, view, update, and delete todos
3. Users can only access their own todos
4. UI is responsive and accessible
5. All tests pass
6. Application deploys successfully in Docker
7. No critical security vulnerabilities

## Out of Scope

The following features are NOT required for this version:
- Password reset functionality
- Email verification
- Todo sharing or collaboration
- Todo categories or tags
- Due dates and reminders
- File attachments
- Real-time updates
- Mobile native apps
- Third-party integrations

## Example User Flow

1. User visits the application
2. User clicks "Register" and creates account
3. System redirects to login page
4. User logs in with credentials
5. User sees empty dashboard
6. User clicks "Add Todo"
7. User enters "Buy groceries" as title
8. User saves the todo
9. Todo appears in the list
10. User checks the completion checkbox
11. Todo shows as completed with visual indicator
12. User can edit or delete the todo
13. User logs out when done
