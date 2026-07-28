# Blog Platform Requirements

## Project Overview

Build a multi-user blogging platform where users can create, publish, and manage blog posts. The platform should support role-based access control (admin, author, reader), commenting system, tag-based categorization, image uploads, and search functionality.

## Target Users

- **Authors**: Users who write and publish blog posts
- **Readers**: Users who read posts and leave comments
- **Administrators**: Users who moderate content and manage the platform

## Functional Requirements

### 1. User Management & Authentication

**User Registration:**
- Users can register with email, username, and password
- Email and username must be unique
- Password must be at least 8 characters with at least one number
- Users assigned "reader" role by default
- Email validation required

**User Login:**
- Users authenticate with email and password
- JWT token issued on successful login (expires in 7 days)
- Support for "Remember me" option (30-day token)
- Failed login attempts tracked (lockout after 5 failures)

**User Profiles:**
- Each user has a profile with:
  - Username (required, unique)
  - Display name (optional)
  - Bio (optional, max 500 characters)
  - Avatar image (optional, uploaded file)
  - Social media links (optional)
  - Join date (auto-generated)
- Users can edit their own profiles
- Public profile pages accessible to all

**Role Management:**
- Three roles: reader, author, admin
- Readers can: read posts, comment, edit own profile
- Authors can: all reader permissions + create/edit/publish own posts
- Admins can: all author permissions + moderate all content, manage users
- Role changes require admin privileges

### 2. Blog Post Management

**Create Post:**
- Authors can create draft posts
- Post fields:
  - Title (required, max 200 characters)
  - Slug (auto-generated from title, editable, unique)
  - Content (required, markdown supported, max 50,000 characters)
  - Excerpt (optional, max 300 characters, auto-generated if empty)
  - Cover image (optional, file upload)
  - Status (draft, published, archived)
  - Tags (multiple, create new or select existing)
  - Published date (auto-set on publish)
  - Updated date (auto-updated on edit)
  - Author (auto-assigned to creator)
  - View count (tracked, read-only)

**Edit Post:**
- Authors can edit their own draft or published posts
- Admins can edit any post
- Editing published post updates "updated_at" timestamp
- Previous versions not tracked (no revision history)

**Publish/Unpublish Post:**
- Authors can publish their draft posts
- Publishing sets status to "published" and sets published_at
- Authors can unpublish (return to draft) their posts
- Admins can publish/unpublish any post

**Delete Post:**
- Authors can delete their own draft posts
- Admins can delete any post (including published)
- Deletion also removes all associated comments
- Soft delete preferred (archived status)

**View Posts:**
- Public homepage lists all published posts (paginated, 10 per page)
- Posts displayed in reverse chronological order
- Show title, excerpt, cover image, author, published date, tags, comment count
- Individual post view shows full content + comments
- View counter increments on each unique view (track by IP or session)

### 3. Commenting System

**Add Comment:**
- Authenticated users can comment on published posts
- Comment fields:
  - Content (required, max 1000 characters)
  - Post ID (auto-assigned)
  - User ID (auto-assigned)
  - Created timestamp (auto-generated)
  - Status (approved, pending, flagged)

**View Comments:**
- Comments displayed under post in chronological order
- Show commenter name, avatar, comment content, timestamp
- Display comment count per post

**Moderate Comments:**
- Authors can moderate comments on their own posts
- Admins can moderate all comments
- Moderation actions: approve, flag, delete
- Flagged comments hidden from public view

**Delete Comment:**
- Users can delete their own comments
- Authors can delete comments on their posts
- Admins can delete any comment

### 4. Tags & Categorization

**Tag Management:**
- Authors create tags when writing posts
- Tags have: name (unique), slug (auto-generated), post count
- Maximum 10 tags per post
- Display popular tags on sidebar (top 20 by usage)

**Tag Pages:**
- Each tag has a dedicated page listing all posts with that tag
- Paginated display (10 posts per page)
- Show tag name and post count

### 5. Search & Discovery

**Search Posts:**
- Full-text search across post titles, content, and author names
- Search bar on homepage and navbar
- Results paginated (10 per page)
- Results ranked by relevance

**Filter Posts:**
- Filter by author
- Filter by tag
- Filter by date range (last week, month, year)
- Filters can be combined

**Popular Posts:**
- Widget showing top 5 most viewed posts (last 30 days)
- Widget showing latest 5 published posts

### 6. Image Upload

**Upload Cover Images:**
- Authors can upload cover images for posts
- Supported formats: JPEG, PNG, WebP
- Maximum file size: 5 MB
- Images auto-resized to max width 1200px (maintain aspect ratio)
- Images stored in local filesystem or cloud storage

**Upload Avatar Images:**
- Users can upload profile avatars
- Supported formats: JPEG, PNG
- Maximum file size: 2 MB
- Images auto-cropped to square and resized to 200x200px

## Technical Requirements

### Backend (FastAPI)

**Framework & Tools:**
- FastAPI for REST API
- Python 3.11+
- SQLAlchemy ORM
- Alembic for migrations
- Pydantic for validation
- PostgreSQL for database

**API Endpoints:**

Authentication:
```
POST /auth/register - Register new user
POST /auth/login - Login user
POST /auth/logout - Logout user
GET /auth/me - Get current user info
PUT /auth/me - Update current user profile
POST /auth/upload-avatar - Upload avatar image
```

Posts:
```
GET /posts - List published posts (paginated, filterable)
GET /posts/{slug} - Get single post by slug
POST /posts - Create new post (author/admin)
PUT /posts/{id} - Update post (author/admin)
DELETE /posts/{id} - Delete post (author/admin)
PATCH /posts/{id}/publish - Publish post (author/admin)
PATCH /posts/{id}/unpublish - Unpublish post (author/admin)
GET /posts/author/{username} - List posts by author
POST /posts/{id}/upload-cover - Upload cover image
```

Comments:
```
GET /posts/{id}/comments - List comments for post
POST /posts/{id}/comments - Add comment (authenticated)
PUT /comments/{id} - Edit comment (own only)
DELETE /comments/{id} - Delete comment (own/author/admin)
PATCH /comments/{id}/moderate - Moderate comment (author/admin)
```

Tags:
```
GET /tags - List all tags
GET /tags/{slug} - Get posts by tag
GET /tags/popular - Get popular tags
```

Users:
```
GET /users/{username} - Get public user profile
GET /users/{username}/posts - List user's published posts
PUT /users/{id}/role - Update user role (admin only)
```

Search:
```
GET /search?q=query - Search posts
```

**Security:**
- JWT authentication for protected routes
- Password hashing with bcrypt
- Role-based access control (RBAC)
- Input validation and sanitization
- Rate limiting on API endpoints
- CORS configuration
- File upload validation (type, size)

**Database Schema:**

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(200),
    bio TEXT,
    avatar_url VARCHAR(500),
    role VARCHAR(20) DEFAULT 'reader',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(250) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    excerpt TEXT,
    cover_image_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'draft',
    author_id INTEGER REFERENCES users(id),
    view_count INTEGER DEFAULT 0,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    slug VARCHAR(60) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE post_tags (
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'approved',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_posts_slug ON posts(slug);
CREATE INDEX idx_posts_author ON posts(author_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_comments_post ON comments(post_id);
CREATE INDEX idx_users_username ON users(username);
```

### Frontend (Next.js)

**Framework & Tools:**
- Next.js 14+ with App Router
- React 18+
- TypeScript
- Tailwind CSS for styling
- Markdown editor for post content
- Image optimization

**Pages:**

1. **Home Page** (`/`)
   - List of published posts (paginated)
   - Search bar
   - Popular tags sidebar
   - Popular posts widget
   - Filter options

2. **Post Detail Page** (`/posts/[slug]`)
   - Full post content with markdown rendering
   - Author info sidebar
   - Comments section
   - Related posts (same tags)
   - Share buttons

3. **Create/Edit Post Page** (`/posts/new`, `/posts/[id]/edit`)
   - Protected route (author/admin only)
   - Title input
   - Markdown editor for content
   - Excerpt textarea
   - Cover image upload with preview
   - Tag selector (create new or select existing)
   - Draft/Publish buttons
   - Preview mode

4. **Author Dashboard** (`/dashboard`)
   - Protected route (author/admin only)
   - List of user's posts (all statuses)
   - Quick stats (total posts, views, comments)
   - Create new post button

5. **Login Page** (`/login`)
   - Email and password fields
   - Remember me checkbox
   - Link to registration

6. **Registration Page** (`/register`)
   - Email, username, password, confirm password fields
   - Link to login

7. **User Profile Page** (`/users/[username]`)
   - Public profile info
   - User's published posts
   - Edit profile button (if own profile)

8. **Edit Profile Page** (`/profile/edit`)
   - Protected route
   - Update display name, bio, avatar
   - Social media links

9. **Tag Page** (`/tags/[slug]`)
   - Posts filtered by tag
   - Tag name and post count

10. **Search Results Page** (`/search`)
    - Search results from query
    - Pagination

11. **Admin Dashboard** (`/admin`)
    - Protected route (admin only)
    - Manage all posts
    - Moderate comments
    - Manage users and roles

**UI/UX Requirements:**
- Responsive design (mobile, tablet, desktop)
- Dark mode support (optional)
- Loading skeletons for content
- Toast notifications for actions
- Markdown preview in post editor
- Image upload with drag-and-drop
- Accessible (WCAG AA)
- SEO optimization (meta tags, Open Graph)

## Non-Functional Requirements

**Performance:**
- API response time < 300ms
- Page load time < 2 seconds
- Support 500 concurrent users
- Image optimization (lazy loading, WebP format)
- Database query optimization (proper indexes)

**Security:**
- All passwords hashed
- JWT tokens for authentication
- Role-based authorization
- SQL injection prevention
- XSS prevention
- CSRF protection
- Rate limiting (prevent abuse)
- Secure file uploads

**Reliability:**
- Database transactions for consistency
- Error handling throughout
- Logging for debugging
- Backup strategy for database

**Scalability:**
- Pagination for all lists
- Efficient database queries
- Image storage scalable (S3-ready)

**Usability:**
- Intuitive navigation
- Clear error messages
- Helpful form validation
- Markdown editor with toolbar
- Mobile-friendly interface

## Deployment Requirements

**Docker Configuration:**
- PostgreSQL container (postgres:15)
- Backend container (FastAPI)
- Frontend container (Next.js)
- Volume for image storage
- Docker Compose orchestration

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection
- `JWT_SECRET_KEY` - JWT signing secret
- `UPLOAD_DIR` - Image upload directory
- `MAX_UPLOAD_SIZE` - File size limit
- `API_URL` - Backend URL for frontend
- `NEXT_PUBLIC_API_URL` - Frontend API endpoint

## Testing Requirements

**Backend Tests:**
- Unit tests for all services
- Integration tests for all API endpoints
- Test authentication and authorization
- Test file uploads
- Test coverage > 80%

**Frontend Tests:**
- Component tests for major UI components
- Integration tests for user flows
- Test accessibility
- Test coverage > 70%

## Success Criteria

1. Users can register, login, and manage profiles
2. Authors can create, edit, publish blog posts with images
3. Readers can view posts, search, filter by tags
4. Users can comment on posts
5. Authors can moderate comments on their posts
6. Admins can manage all content and users
7. UI is responsive and accessible
8. All tests pass
9. Application deploys successfully in Docker

## Out of Scope

- Social login (OAuth)
- Email notifications
- Post scheduling
- Multi-language support
- Real-time collaboration
- Post analytics dashboard
- Newsletter subscriptions
- Content recommendations (ML)
- Mobile apps

## Example User Flows

**Author Publishing Post:**
1. Author logs in
2. Navigates to dashboard
3. Clicks "Create New Post"
4. Enters title, content (markdown)
5. Uploads cover image
6. Adds tags
7. Clicks "Publish"
8. Post appears on homepage

**Reader Commenting:**
1. Reader browses homepage
2. Clicks on post title
3. Reads post content
4. Scrolls to comments section
5. Enters comment text
6. Clicks "Post Comment"
7. Comment appears under post

**Admin Moderating Content:**
1. Admin logs in
2. Navigates to admin dashboard
3. Sees flagged comments
4. Reviews comment content
5. Clicks "Approve" or "Delete"
6. Comment status updated
