# Example Applications

This directory contains comprehensive example applications that demonstrate the Supervised Agentic Workflow System's capabilities. Each example includes:

1. **requirements.md** - Clear specifications for the application
2. **expected_output.md** - Documentation of what the system should generate
3. Demonstrations of different complexity levels

## Available Examples

### 1. Simple Todo App (Beginner)
**Complexity:** Basic  
**Path:** `./todo-app/`  
**Features:** CRUD operations, basic authentication  
**Demonstrates:** Core workflow functionality, basic database operations

A simple task management application showcasing:
- User authentication and registration
- Create, read, update, delete todo items
- PostgreSQL database integration
- RESTful API design
- Basic React UI with forms and lists

**Estimated Generation Time:** 3-5 minutes

---

### 2. Blog Platform (Intermediate)
**Complexity:** Medium  
**Path:** `./blog-platform/`  
**Features:** Multi-user blog with authentication, comments, tags  
**Demonstrates:** Complex data relationships, role-based access, file uploads

A blogging platform featuring:
- User authentication with roles (admin, author, reader)
- Create, edit, publish blog posts with markdown support
- Comments system with moderation
- Tag-based categorization
- Image upload for post covers
- Search functionality

**Estimated Generation Time:** 5-8 minutes

---

### 3. E-Commerce App (Advanced)
**Complexity:** Complex  
**Path:** `./ecommerce-app/`  
**Features:** Shopping cart, payment integration, order management  
**Demonstrates:** Complex business logic, external API integration, advanced state management

A full-featured e-commerce platform with:
- Product catalog with categories and search
- Shopping cart with session management
- User authentication and profile management
- Order processing and history
- Payment integration (Stripe mock)
- Admin dashboard for product/order management
- Email notifications
- Inventory management

**Estimated Generation Time:** 10-15 minutes

---

## How to Use These Examples

### Running an Example

1. **Navigate to the project root:**
   ```bash
   cd visitor_workflow
   ```

2. **Run the workflow with an example requirements file:**
   ```bash
   python main.py examples/todo-app/requirements.md
   ```

3. **Monitor the workflow execution:**
   - Watch as the Planning Agent decomposes requirements
   - See agents coordinate through the Supervisor
   - Observe self-evaluation and testing phases
   - View deployment status when complete

### What to Expect

Each example will generate:
- **Backend code** in `./backend/` directory
  - FastAPI application with routes, models, services
  - Database models and migrations
  - Unit and integration tests
  - Configuration files
  
- **Frontend code** in `./frontend/` directory
  - Next.js application with pages and components
  - Responsive UI with accessibility features
  - API integration layer
  - Component tests
  
- **Database containers** via Docker
  - PostgreSQL for relational data
  - MongoDB for unstructured data (if needed)
  
- **Deployment configurations**
  - Docker Compose files
  - Environment configuration
  - Service orchestration

### Customizing Examples

You can modify the requirements files to:
- Add or remove features
- Change technology preferences
- Adjust complexity
- Specify design requirements

The workflow system will adapt the generated code accordingly.

---

## Example Walkthrough Videos

### Todo App Walkthrough
*Coming soon: Animated GIF showing workflow execution*

**Key Steps:**
1. Requirements analysis (10s)
2. Backend generation with FastAPI (45s)
3. Frontend generation with Next.js (45s)
4. Database initialization (15s)
5. Testing phase (30s)
6. Deployment to Docker (25s)

### Blog Platform Walkthrough
*Coming soon: Animated GIF showing workflow execution*

**Key Steps:**
1. Complex requirements decomposition (20s)
2. Multi-model backend generation (90s)
3. Feature-rich frontend generation (90s)
4. Advanced testing with integration tests (60s)
5. Full deployment with multiple containers (40s)

### E-Commerce Walkthrough
*Coming soon: Animated GIF showing workflow execution*

**Key Steps:**
1. Enterprise-level planning (30s)
2. Complex backend with business logic (120s)
3. Advanced frontend with state management (120s)
4. Payment integration setup (45s)
5. Comprehensive testing suite (90s)
6. Production-ready deployment (60s)

---

## Comparison Matrix

| Feature | Todo App | Blog Platform | E-Commerce |
|---------|----------|---------------|------------|
| **Complexity** | Basic | Medium | Advanced |
| **Database Tables** | 2 | 5 | 10+ |
| **API Endpoints** | 8 | 20+ | 40+ |
| **Frontend Pages** | 3 | 8 | 15+ |
| **Authentication** | Basic | Role-based | Multi-level |
| **External APIs** | None | None | Payment (Stripe) |
| **File Uploads** | No | Yes | Yes |
| **Real-time Features** | No | No | Optional |
| **Admin Dashboard** | No | Yes | Yes |
| **Email Notifications** | No | No | Yes |
| **Search Functionality** | No | Yes | Yes |
| **Generation Time** | 3-5 min | 5-8 min | 10-15 min |

---

## Troubleshooting

### Common Issues

**Issue:** Workflow fails during database initialization  
**Solution:** Ensure Docker is running: `docker ps`

**Issue:** Frontend build errors  
**Solution:** Check Node.js version (requires 18+): `node --version`

**Issue:** Backend type checking fails  
**Solution:** Review generated code in `./backend/` and check error logs

**Issue:** Tests fail after generation  
**Solution:** This is normal - the Testing Agent will report failures to the Supervisor, which routes back to the appropriate agent for fixes

### Getting Help

- Review workflow logs in the console output
- Check `workflow_checkpoints.db` for saved state
- Use `--resume` flag to continue interrupted workflows
- Consult the main README.md for configuration options

---

## Contributing Examples

Want to add your own example? Follow this structure:

```
examples/
└── your-app-name/
    ├── requirements.md          # Clear, detailed requirements
    ├── expected_output.md       # Documentation of expected results
    └── screenshots/             # Optional: UI mockups or diagrams
```

Submit a pull request with your example!

---

## Learning Path

**Recommended order for learning:**

1. **Start with Todo App** - Understand basic workflow mechanics
2. **Progress to Blog Platform** - Learn complex data relationships
3. **Tackle E-Commerce** - Master advanced integrations and business logic

Each example builds on concepts from the previous ones.

---

## Additional Resources

- [Main README](../README.md) - System overview and installation
- [Quickstart Guide](../QUICKSTART.md) - Getting started quickly
- [Monitoring Guide](../MONITORING_GUIDE.md) - Understanding workflow execution
- [Configuration Guide](../demo_config_output/CONFIGURATION_GUIDE.md) - Environment setup

---

*Last updated: January 2025*
