# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Configure API Key

Edit the `.env` file and add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

### Step 2: Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 3: Run Your First Workflow

#### Option A: Simple Text Requirements

```bash
python main.py "Build a todo app with user authentication and CRUD operations"
```

#### Option B: Markdown File Requirements

```bash
python main.py ./example_requirements.md
```

### Step 4: Watch the Magic! ✨

You'll see output like:

```
==============================================================================
🤖 Supervised Agentic Workflow System
==============================================================================

📝 Requirements: Build a todo app with user authentication...

🔧 Initializing workflow graph...
✅ Workflow graph created

🆔 Thread ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

🚀 Starting workflow execution...
------------------------------------------------------------------------------

🎯 Planning Agent: Analyzing requirements...
✅ Created execution plan with 8 tasks
   - task_1: Initialize PostgreSQL database (agent: database)
   - task_2: Create User and Todo models (agent: backend)
   - task_3: Implement authentication endpoints (agent: backend)
   - task_4: Implement CRUD endpoints for todos (agent: backend)
   - task_5: Create login and register pages (agent: frontend)
   - task_6: Create todo list UI with CRUD (agent: frontend)
   - task_7: Run comprehensive tests (agent: testing)
   - task_8: Deploy to Docker (agent: deployment)

👁️  Supervisor: Determining next agent...
   Progress: 0.0%
   Next agent: database_node

🗄️  Database Agent: Initializing databases...

...

✅ Workflow completed successfully!

📊 Workflow Summary:
   Status: complete
   Tasks completed: 8
   Agent transitions: 15

🚀 Deployment Info:
   Frontend: http://localhost:3000
   Backend: http://localhost:8000
   Containers: frontend, backend, postgres, mongo
```

## 📁 What Gets Generated

After a successful workflow execution, you'll have:

```
visitor_workflow/
├── backend/           # ⬅️ Generated FastAPI code
│   ├── main.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── requirements.txt
│
├── frontend/          # ⬅️ Generated Next.js code
│   ├── pages/
│   ├── components/
│   ├── styles/
│   └── package.json
│
└── docker-compose.yml # ⬅️ Generated deployment config
```

## 🎯 Current Status

**What Works Now:**
- ✅ Planning Agent analyzes requirements (text or markdown files)
- ✅ Creates execution plan with task dependencies
- ✅ Supervisor routes between agents
- ✅ State persistence with checkpointing
- ✅ Progress tracking and logging

**What's Coming Next:**
- 🚧 Full code generation in Backend/Frontend agents
- 🚧 Docker integration in Database/Deployment agents
- 🚧 Test generation and execution
- 🚧 Self-evaluation loops with quality gates

## 📖 Next Steps

1. **Review the Plan**: Check the execution plan created by the Planning Agent
2. **Explore the Spec**: See `.kiro/specs/supervised-agentic-workflow/` for full requirements and design
3. **Customize**: Edit `.env` to change ports, database versions, retry limits, etc.
4. **Extend**: Add new specialist agents by following the pattern in `workflow/agents/`

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'langgraph'"
```bash
pip install -r requirements.txt
```

### "openai.AuthenticationError"
- Check your `.env` file has the correct `OPENAI_API_KEY`
- Make sure the key starts with `sk-`

### "Planning Agent failed"
- Ensure you have internet connection (for OpenAI API)
- Check your API key is valid and has credits
- Try a simpler requirement to test

## 💡 Tips

1. **Start Simple**: Test with a simple requirement first to verify setup
2. **Use Markdown**: For complex requirements, use a markdown file for better organization
3. **Check Logs**: The workflow prints detailed logs at each step
4. **Thread IDs**: Save thread IDs to resume interrupted workflows later

## 🆘 Need Help?

- Check `README.md` for detailed documentation
- Review `IMPLEMENTATION_STATUS.md` for current capabilities
- See `example_requirements.md` for sample requirements format
- Open an issue on GitHub for bugs or questions

Happy building! 🎉
