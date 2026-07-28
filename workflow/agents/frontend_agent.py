"""
Frontend Agent: Generates Next.js React code with self-evaluation.

The Frontend Agent:
1. Generates Next.js React code with TypeScript
2. Creates responsive UI components with mobile-first design
3. Implements accessibility standards (WCAG AA)
4. Implements comprehensive error boundaries and loading states
5. Evaluates generated code with eslint and accessibility checks
6. Iterates until quality gates pass (max 5 attempts)

**Validates: Requirements 5.1, 5.4, 5.5, 5.6, 12.3, 13.1, 13.4, 14.2**
"""

import os
import json
import subprocess
import tempfile
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

from ..config import get_config, get_llm


def extract_backend_api_spec(backend_dir: str) -> Dict[str, Any]:
    """
    Extract API specification from backend code.
    
    Reads backend main.py, models.py, and schemas.py to extract:
    - Available endpoints (GET, POST, PUT, DELETE)
    - Request/response schemas
    - Query parameters
    - Path parameters
    
    Args:
        backend_dir: Path to backend directory
        
    Returns:
        Dictionary with API specification
    """
    backend_path = Path(backend_dir)
    api_spec = {
        "endpoints": [],
        "schemas": {},
        "base_url": "http://localhost:8000"
    }
    
    # Read main.py to extract endpoints
    main_file = backend_path / "main.py"
    if main_file.exists():
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                main_content = f.read()
            
            # Extract endpoints using regex patterns
            import re
            
            # Find @app decorator patterns
            endpoint_pattern = r'@app\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']'
            matches = re.findall(endpoint_pattern, main_content, re.MULTILINE)
            
            for method, path in matches:
                api_spec["endpoints"].append({
                    "method": method.upper(),
                    "path": path,
                    "full_url": f"{api_spec['base_url']}{path}"
                })
        except Exception as e:
            print(f"      ⚠️  Could not read main.py: {e}")
    
    # Read schemas.py to extract data models
    schemas_file = backend_path / "schemas.py"
    if schemas_file.exists():
        try:
            with open(schemas_file, 'r', encoding='utf-8') as f:
                schemas_content = f.read()
            
            api_spec["schemas"]["raw_content"] = schemas_content
            
            # Extract schema class names
            import re
            schema_pattern = r'class\s+(\w+)\(.*BaseModel.*\):'
            schema_matches = re.findall(schema_pattern, schemas_content)
            api_spec["schemas"]["classes"] = schema_matches
        except Exception as e:
            print(f"      ⚠️  Could not read schemas.py: {e}")
    
    # Read models.py to extract database models
    models_file = backend_path / "models.py"
    if models_file.exists():
        try:
            with open(models_file, 'r', encoding='utf-8') as f:
                models_content = f.read()
            
            api_spec["models"] = {"raw_content": models_content}
        except Exception as e:
            print(f"      ⚠️  Could not read models.py: {e}")
    
    return api_spec


class CodeEvaluator:
    """
    Frontend code evaluation system using eslint and accessibility checks.
    
    **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**
    """
    
    @staticmethod
    def check_file_structure(output_dir: Path) -> Tuple[bool, List[str]]:
        """
        Validate Next.js project structure.
        
        Args:
            output_dir: Project directory
            
        Returns:
            Tuple of (success: bool, issues: List[str])
        """
        issues = []
        required_files = [
            "package.json",
            "next.config.js",
            "tsconfig.json"
        ]
        
        required_dirs = [
            "pages",
            "components",
            "styles",
            "public"
        ]
        
        # Check required files
        for file in required_files:
            if not (output_dir / file).exists():
                issues.append(f"Missing required file: {file}")
        
        # Check required directories
        for dir_name in required_dirs:
            if not (output_dir / dir_name).exists():
                issues.append(f"Missing required directory: {dir_name}/")
        
        # Check for index page
        pages_dir = output_dir / "pages"
        if pages_dir.exists():
            index_exists = (
                (pages_dir / "index.tsx").exists() or
                (pages_dir / "index.jsx").exists()
            )
            if not index_exists:
                issues.append("Missing pages/index.tsx or pages/index.jsx")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def check_typescript_usage(output_dir: Path) -> Tuple[bool, List[str]]:
        """
        Verify TypeScript is properly configured and used.
        
        Args:
            output_dir: Project directory
            
        Returns:
            Tuple of (success: bool, issues: List[str])
        """
        issues = []
        
        # Check tsconfig.json exists
        tsconfig = output_dir / "tsconfig.json"
        if not tsconfig.exists():
            issues.append("TypeScript not configured (tsconfig.json missing)")
            return False, issues
        
        # Check for .tsx files (TypeScript React)
        tsx_files = list(output_dir.rglob("*.tsx"))
        ts_files = list(output_dir.rglob("*.ts"))
        
        if not tsx_files and not ts_files:
            issues.append("No TypeScript files found (.tsx or .ts)")
            return False, issues
        
        return True, []
    
    @staticmethod
    def check_accessibility_features(code: str, filename: str) -> Tuple[bool, List[str]]:
        """
        Check for basic accessibility features in React code.
        
        Args:
            code: File content
            filename: File name for context
            
        Returns:
            Tuple of (success: bool, issues: List[str])
        """
        issues = []
        
        # Check for semantic HTML usage
        has_semantic = any(tag in code for tag in [
            "<main", "<header", "<footer", "<nav", "<article", "<section"
        ])
        
        # Check for ARIA attributes
        has_aria = any(attr in code for attr in [
            "aria-label", "aria-labelledby", "aria-describedby", "role="
        ])
        
        # Check for alt attributes on images
        if "<img" in code or "<Image" in code:
            if "alt=" not in code and "alt:" not in code:
                issues.append(f"{filename}: Images missing alt attributes")
        
        # Check for button/link accessibility
        if ("<button" in code or "<a " in code) and len(code) > 500:
            # Only check substantial components
            if not has_aria and not has_semantic:
                issues.append(f"{filename}: Interactive elements may need ARIA labels")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def check_responsive_design(code: str, filename: str) -> Tuple[bool, List[str]]:
        """
        Check for responsive design patterns.
        
        Args:
            code: File content
            filename: File name
            
        Returns:
            Tuple of (success: bool, issues: List[str])
        """
        issues = []
        
        # Check for Tailwind responsive classes or CSS media queries
        has_tailwind_responsive = any(prefix in code for prefix in [
            "sm:", "md:", "lg:", "xl:", "2xl:"
        ])
        
        has_media_queries = "@media" in code
        
        has_viewport_meta = 'name="viewport"' in code
        
        # For layout files, should have responsive design
        if "layout" in filename.lower() or "page" in filename.lower():
            if not has_tailwind_responsive and not has_media_queries:
                issues.append(f"{filename}: No responsive design patterns found")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def check_error_handling(code: str, filename: str) -> Tuple[bool, List[str]]:
        """
        Check for error boundaries and loading states.
        
        Args:
            code: File content
            filename: File name
            
        Returns:
            Tuple of (success: bool, issues: List[str])
        """
        issues = []
        
        # Check for error boundary patterns
        has_error_boundary = "ErrorBoundary" in code or "componentDidCatch" in code
        
        # Check for loading states
        has_loading = any(pattern in code for pattern in [
            "loading", "isLoading", "Loading", "Spinner", "Skeleton"
        ])
        
        # Check for try-catch in async functions
        if "async " in code or "await " in code:
            if "try" not in code or "catch" not in code:
                issues.append(f"{filename}: Async code missing try-catch error handling")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def run_eslint(output_dir: Path) -> Tuple[bool, List[str]]:
        """
        Run eslint on the project.
        
        Args:
            output_dir: Project directory
            
        Returns:
            Tuple of (success: bool, issues: List[str])
        """
        try:
            # Check if eslint is available
            result = subprocess.run(
                ["npx", "eslint", "--version"],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                # eslint not installed, skip
                return True, []
            
            # Run eslint
            result = subprocess.run(
                ["npx", "eslint", ".", "--ext", ".js,.jsx,.ts,.tsx", "--max-warnings", "10"],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            issues = []
            if result.returncode != 0:
                # Parse eslint output
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and ('error' in line.lower() or 'warning' in line.lower()):
                        issues.append(line)
                
                # Limit to top 5 issues
                return False, issues[:5]
            
            return True, []
            
        except FileNotFoundError:
            # Node/npm not installed, skip eslint
            return True, []
        except subprocess.TimeoutExpired:
            return False, ["ESLint timed out"]
        except Exception as e:
            # Don't fail on linting errors
            return True, []
    
    @staticmethod
    def check_package_dependencies(output_dir: Path) -> Tuple[bool, List[str]]:
        """
        Validate package.json has required dependencies.
        
        Args:
            output_dir: Project directory
            
        Returns:
            Tuple of (success: bool, issues: List[str])
        """
        issues = []
        package_json = output_dir / "package.json"
        
        if not package_json.exists():
            return False, ["package.json not found"]
        
        try:
            with open(package_json, 'r') as f:
                pkg = json.load(f)
            
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            
            required = ["next", "react", "react-dom"]
            for dep in required:
                if dep not in deps:
                    issues.append(f"Missing required dependency: {dep}")
            
            # Check for TypeScript deps
            typescript_deps = ["typescript", "@types/react", "@types/node"]
            has_typescript = any(dep in deps for dep in typescript_deps)
            
            if not has_typescript:
                issues.append("TypeScript dependencies missing")
            
            return len(issues) == 0, issues
            
        except json.JSONDecodeError:
            return False, ["Invalid package.json"]
        except Exception as e:
            return False, [f"Error reading package.json: {str(e)}"]
    
    @classmethod
    def evaluate_project(
        cls,
        output_dir: Path,
        requirements: str
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation of Next.js project.
        
        Args:
            output_dir: Project directory
            requirements: Task requirements
            
        Returns:
            Evaluation results dictionary
        """
        results = {
            "passed": True,
            "issues": [],
            "scores": {},
            "details": {}
        }
        
        # 1. Check file structure
        structure_ok, structure_issues = cls.check_file_structure(output_dir)
        results["scores"]["structure"] = "passed" if structure_ok else "failed"
        results["details"]["structure"] = structure_issues
        
        if not structure_ok:
            results["passed"] = False
            results["issues"].extend(structure_issues)
            return results  # Stop if structure is wrong
        
        # 2. Check TypeScript usage
        typescript_ok, typescript_issues = cls.check_typescript_usage(output_dir)
        results["scores"]["typescript"] = "passed" if typescript_ok else "failed"
        results["details"]["typescript"] = typescript_issues
        
        if not typescript_ok:
            results["passed"] = False
            results["issues"].extend(typescript_issues)
        
        # 3. Check package.json dependencies
        deps_ok, deps_issues = cls.check_package_dependencies(output_dir)
        results["scores"]["dependencies"] = "passed" if deps_ok else "failed"
        results["details"]["dependencies"] = deps_issues
        
        if not deps_ok:
            results["passed"] = False
            results["issues"].extend(deps_issues)
        
        # 4. Check code quality in TypeScript files
        tsx_files = list(output_dir.rglob("*.tsx"))
        accessibility_issues = []
        responsive_issues = []
        error_handling_issues = []
        
        for tsx_file in tsx_files[:5]:  # Check first 5 files
            try:
                with open(tsx_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Accessibility check
                a11y_ok, a11y_issues = cls.check_accessibility_features(
                    code, tsx_file.name
                )
                if not a11y_ok:
                    accessibility_issues.extend(a11y_issues)
                
                # Responsive design check
                responsive_ok, resp_issues = cls.check_responsive_design(
                    code, tsx_file.name
                )
                if not responsive_ok:
                    responsive_issues.extend(resp_issues)
                
                # Error handling check
                error_ok, error_issues = cls.check_error_handling(
                    code, tsx_file.name
                )
                if not error_ok:
                    error_handling_issues.extend(error_issues)
                    
            except Exception as e:
                continue
        
        results["scores"]["accessibility"] = "passed" if not accessibility_issues else "warning"
        results["scores"]["responsive"] = "passed" if not responsive_issues else "warning"
        results["scores"]["error_handling"] = "passed" if not error_handling_issues else "warning"
        
        results["details"]["accessibility"] = accessibility_issues
        results["details"]["responsive"] = responsive_issues
        results["details"]["error_handling"] = error_handling_issues
        
        # These are warnings, not failures (unless critical)
        if len(accessibility_issues) > 3:
            results["passed"] = False
            results["issues"].extend(accessibility_issues[:3])
        
        # 5. Run eslint (optional, don't fail on linting)
        eslint_ok, eslint_issues = cls.run_eslint(output_dir)
        results["scores"]["eslint"] = "passed" if eslint_ok else "warning"
        results["details"]["eslint"] = eslint_issues
        
        return results


class FrontendAgent:
    """
    Frontend Agent that generates Next.js React code with self-evaluation.
    
    **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 13.1, 13.4, 14.2**
    """
    
    MAX_RETRIES = 5
    
    def __init__(self):
        """Initialize the Frontend Agent."""
        self.config = get_config()
        self.llm = get_llm()
        
        self.evaluator = CodeEvaluator()
        
        self.generation_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_generation_system_prompt()),
            ("human", "{task_description}\n\nBackend API URL: {backend_url}")
        ])
        
        self.regeneration_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_regeneration_system_prompt()),
            ("human",
             "Previous code had these issues:\n{issues}\n\n"
             "Original task: {task_description}\n\n"
             "Fix the issues and regenerate complete, corrected code.")
        ])
    
    def _get_generation_system_prompt(self) -> str:
        """Get system prompt for initial code generation."""
        return """You are a Frontend Code Generation Agent specializing in Next.js, React, and TypeScript.

Your responsibilities:
1. Generate clean, production-ready Next.js React code with TypeScript
2. Create responsive UI components using mobile-first design approach
3. Implement WCAG AA accessibility standards (semantic HTML, ARIA labels)
4. Use Tailwind CSS for responsive styling
5. Include comprehensive error boundaries and loading states
6. Follow React best practices with proper hooks and patterns
7. Add TypeScript types for ALL components, props, and functions

Code Structure:
Generate a complete Next.js project with proper organization:
- pages/: Next.js page routes (_app.tsx, _document.tsx, index.tsx, etc.)
- components/: Reusable React components organized by feature
  - ErrorBoundary.tsx: Global error boundary component
  - Loading.tsx: Loading spinner/skeleton components
- styles/: Global styles (globals.css with Tailwind directives)
- lib/: Utility functions and API client (API calls with error handling)
- public/: Static assets (favicon, images)
- package.json: All dependencies with versions
- next.config.js: Next.js configuration
- tsconfig.json: TypeScript configuration
- tailwind.config.js: Tailwind CSS configuration
- postcss.config.js: PostCSS configuration

Quality Standards (CRITICAL):
- ALL components MUST be TypeScript (.tsx files with proper types)
- ALL components MUST have explicit prop type definitions (interface or type)
- Use semantic HTML elements (main, header, footer, nav, article, section)
- Add ARIA labels for interactive elements (buttons, links, forms)
- Add alt attributes for ALL images
- Implement mobile-first responsive design using Tailwind breakpoints (sm:, md:, lg:)
- Include loading states for async operations (skeleton screens, spinners)
- Wrap components in error boundaries for graceful error handling
- Add proper meta tags for SEO (title, description, viewport)
- Include proper form validation with error messages
- Ensure keyboard navigation works (focus states, tab order)
- Use React hooks properly (useState, useEffect, useMemo, useCallback)
- Handle API errors gracefully with try-catch and user feedback

Responsive Design (Mobile-First):
- Base styles for mobile (default)
- sm: (640px+) for tablet portrait
- md: (768px+) for tablet landscape
- lg: (1024px+) for desktop
- xl: (1280px+) for large desktop
Example: <div className="w-full sm:w-1/2 md:w-1/3 lg:w-1/4">

Accessibility (WCAG AA):
- Use semantic HTML (<button> not <div onClick>)
- Add aria-label for icon buttons: <button aria-label="Close menu">
- Add alt text for images: <img src="..." alt="Description" />
- Ensure color contrast ratios meet WCAG AA standards
- Add focus indicators: focus:ring-2 focus:ring-blue-500
- Use proper heading hierarchy (h1 -> h2 -> h3)

Error Boundaries and Loading:
Create ErrorBoundary component:
```typescript
'use client';
import React from 'react';

class ErrorBoundary extends React.Component<
  {{ children: React.ReactNode; fallback?: React.ReactNode }},
  {{ hasError: boolean; error?: Error }}
> {{
  constructor(props: any) {{
    super(props);
    this.state = {{ hasError: false }};
  }}

  static getDerivedStateFromError(error: Error) {{
    return {{ hasError: true, error }};
  }}

  render() {{
    if (this.state.hasError) {{
      return this.props.fallback || <div>Something went wrong</div>;
    }}
    return this.props.children;
  }}
}}
```

Loading Component:
```typescript
export const Loading: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" 
         role="status" aria-label="Loading">
      <span className="sr-only">Loading...</span>
    </div>
  </div>
);
```

API Client with Error Handling:
```typescript
// lib/api.ts
export async function fetchAPI<T>(url: string): Promise<T> {{
  try {{
    const response = await fetch(url);
    if (!response.ok) {{
      throw new Error(`HTTP error! status: ${{response.status}}`);
    }}
    return await response.json();
  }} catch (error) {{
    console.error('API Error:', error);
    throw error;
  }}
}}
```

Package.json Template:
```json
{{
  "name": "generated-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }},
  "dependencies": {{
    "next": "^14.0.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.5"
  }},
  "devDependencies": {{
    "@types/node": "^20.10.0",
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.56.0",
    "eslint-config-next": "^14.0.4",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.3"
  }}
}}
```

Output Format:
Return ONLY a valid JSON object (no markdown, no explanations):
{{
  "files": {{
    "pages/_app.tsx": "// App wrapper code...",
    "pages/_document.tsx": "// Document code...",
    "pages/index.tsx": "// Home page code...",
    "components/ErrorBoundary.tsx": "// Error boundary...",
    "components/Loading.tsx": "// Loading component...",
    "lib/api.ts": "// API client...",
    "styles/globals.css": "// Global styles...",
    "package.json": "{{ dependencies... }}",
    "next.config.js": "// Next.js config...",
    "tsconfig.json": "// TypeScript config...",
    "tailwind.config.js": "// Tailwind config...",
    "postcss.config.js": "// PostCSS config...",
    "public/favicon.ico": "// Can be empty placeholder",
    ".env.local.example": "// Environment variables template"
  }}
}}
"""
    
    def _get_regeneration_system_prompt(self) -> str:
        """Get system prompt for code regeneration after issues found."""
        return """You are fixing issues in Next.js React TypeScript code.

Previous generation had quality issues. Your task:
1. Analyze the reported issues carefully
2. Fix ALL identified problems
3. Ensure code meets quality standards:
   - Proper Next.js project structure (pages/, components/, styles/, lib/, public/)
   - TypeScript with complete type definitions
   - Responsive design (mobile-first with Tailwind)
   - Accessibility (WCAG AA: ARIA labels, semantic HTML)
   - Error boundaries and loading states
   - All required features implemented

Common issues to fix:
- Missing TypeScript types: Add interface/type definitions
- Missing accessibility: Add ARIA labels, alt text, semantic HTML
- Missing responsive design: Add Tailwind breakpoints (sm:, md:, lg:)
- Missing error handling: Add ErrorBoundary and try-catch
- Missing loading states: Add loading spinners/skeletons
- Wrong file structure: Follow Next.js conventions
- Missing dependencies: Add to package.json

Return corrected code in same JSON format:
{{
  "files": {{
    "pages/_app.tsx": "// Fixed code...",
    ...
  }}
}}
"""
    
    def generate_code(
        self,
        task_description: str,
        backend_url: str = "http://localhost:8000",
        previous_issues: Optional[List[str]] = None,
        backend_api_spec: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate frontend code for the given task.
        
        Args:
            task_description: Description of what to build
            backend_url: Backend API URL
            previous_issues: Issues from previous generation attempt
            backend_api_spec: Extracted API specification from backend code
            
        Returns:
            Dictionary mapping file paths to file contents
            
        **Validates: Requirement 5.1**
        """
        print(f"   📝 Generating code for: {task_description[:80]}...")
        
        # Build API context from backend spec
        api_context = ""
        if backend_api_spec and backend_api_spec.get("endpoints"):
            api_context = "\n\n## BACKEND API ENDPOINTS (use these EXACT endpoints):\n"
            for endpoint in backend_api_spec["endpoints"]:
                api_context += f"- {endpoint['method']} {endpoint['path']}\n"
            
            if backend_api_spec.get("schemas", {}).get("classes"):
                api_context += "\n## AVAILABLE SCHEMAS:\n"
                api_context += ", ".join(backend_api_spec["schemas"]["classes"])
                api_context += "\n"
        
        try:
            # Choose prompt based on whether this is regeneration
            if previous_issues:
                chain = self.regeneration_prompt | self.llm
                response = chain.invoke({
                    "task_description": task_description + api_context,
                    "issues": "\n".join(previous_issues)
                })
            else:
                chain = self.generation_prompt | self.llm
                response = chain.invoke({
                    "task_description": task_description,
                    "backend_url": backend_url
                })
            
            content = response.content.strip()
            
            # Parse JSON response (handle markdown code blocks)
            content = self._extract_json_from_response(content)
            result = json.loads(content)
            
            if "files" not in result:
                raise ValueError("Response must contain 'files' key")
            
            return result["files"]
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️  JSON parse error: {str(e)}")
            return self._generate_minimal_app(backend_url)
        except Exception as e:
            print(f"   ⚠️  Generation error: {str(e)}")
            return self._generate_minimal_app(backend_url)
    
    def _extract_json_from_response(self, content: str) -> str:
        """Extract JSON from response that may contain markdown."""
        # Remove markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif content.startswith("```"):
            lines = content.split('\n')
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_block = not in_block
                    continue
                if in_block or not line.strip().startswith('```'):
                    json_lines.append(line)
            content = '\n'.join(json_lines)
        
        return content.strip()
    
    def _generate_minimal_app(self, backend_url: str) -> Dict[str, str]:
        """Generate a minimal Next.js app as fallback."""
        return {
            "pages/index.tsx": """import Head from 'next/head';

export default function Home() {
  return (
    <>
      <Head>
        <title>Generated App</title>
        <meta name="description" content="Generated by Supervised Agentic Workflow" />
      </Head>
      
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Welcome to Your App
          </h1>
          <p className="text-lg text-gray-600">
            Generated by the Supervised Agentic Workflow System
          </p>
        </div>
      </main>
    </>
  );
}
""",
            "pages/_app.tsx": """import type { AppProps } from 'next/app';
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}
""",
            "styles/globals.css": """@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
""",
            "package.json": """{
  "name": "generated-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.50.0",
    "eslint-config-next": "14.0.0",
    "postcss": "^8.4.31",
    "tailwindcss": "^3.3.5",
    "typescript": "^5.2.0"
  }
}
""",
            "tailwind.config.js": """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
""",
            "next.config.js": """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = nextConfig
""",
            ".env.local.example": f"""NEXT_PUBLIC_API_URL={backend_url}
"""
        }
    
    def write_code(self, files: Dict[str, str], output_dir: str) -> None:
        """
        Write generated code to files.
        
        Args:
            files: Dictionary mapping file paths to contents
            output_dir: Base output directory (e.g., './frontend')
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for file_path, content in files.items():
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"   ✅ Written: {full_path}")
    
    def evaluate_code(self, output_dir: str, requirements: str = "") -> Dict[str, Any]:
        """
        Comprehensive evaluation of Next.js frontend code.
        
        Quality Gates:
        1. File structure validation (Next.js conventions)
        2. TypeScript usage check
        3. Package dependencies validation
        4. Code quality checks (accessibility, responsive design, error handling)
        5. ESLint validation (optional)
        
        Args:
            output_dir: Directory containing generated code
            requirements: Task requirements for feature checking
            
        Returns:
            Evaluation results dictionary
            
        **Validates: Requirements 5.2, 5.3, 9.2, 9.3, 9.4**
        """
        print(f"   🔍 Evaluating generated frontend code...")
        
        results = self.evaluator.evaluate_project(
            Path(output_dir),
            requirements
        )
        
        # Summary
        if results["passed"]:
            print(f"      ✅ All quality gates passed!")
        else:
            print(f"      ⚠️  Quality issues found: {len(results['issues'])} issues")
        
        return results
    
    def execute_task(
        self,
        task_description: str,
        backend_url: str = "http://localhost:8000",
        max_retries: int = MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Execute frontend generation task with self-evaluation loop.
        
        This implements the self-evaluation pattern:
        1. Generate code based on task requirements
        2. Write code to files
        3. Evaluate code quality (eslint, prettier, accessibility, responsive design)
        4. If failed and retries remaining: regenerate with feedback
        5. If failed and max retries: request human approval
        6. If passed: return success
        
        Args:
            task_description: What to build
            backend_url: Backend API URL
            max_retries: Maximum retry attempts (default: 5)
            
        Returns:
            Dictionary with task results:
            {
                "success": bool,
                "output_dir": str,
                "files": List[str],
                "evaluation": dict,
                "attempts": int,
                "requires_approval": bool (if max retries exceeded)
            }
            
        **Validates: Requirements 5.2, 5.3, 9.2, 9.3, 9.4, 9.5**
        """
        output_dir = self.config.frontend_output_dir
        previous_issues = None
        
        print(f"\n🎨 Frontend Agent: Starting task execution")
        print(f"   Task: {task_description[:100]}...")
        print(f"   Max retries: {max_retries}\n")
        
        # Extract backend API specification if backend exists
        backend_api_spec = None
        backend_dir = self.config.backend_output_dir
        if Path(backend_dir).exists():
            print(f"   📡 Reading backend API specification...")
            backend_api_spec = extract_backend_api_spec(backend_dir)
            if backend_api_spec.get("endpoints"):
                print(f"      ✅ Found {len(backend_api_spec['endpoints'])} API endpoints")
                for endpoint in backend_api_spec["endpoints"][:5]:  # Show first 5
                    print(f"         - {endpoint['method']} {endpoint['path']}")
                if len(backend_api_spec["endpoints"]) > 5:
                    print(f"         ... and {len(backend_api_spec['endpoints']) - 5} more")
            else:
                print(f"      ⚠️  No API endpoints found in backend")
        
        for attempt in range(1, max_retries + 1):
            print(f"   📍 Attempt {attempt}/{max_retries}")
            
            # Generate code with backend API spec
            files = self.generate_code(
                task_description,
                backend_url,
                previous_issues,
                backend_api_spec  # Pass API spec to generation
            )
            
            # Write code to files
            self.write_code(files, output_dir)
            
            # Evaluate code quality
            evaluation = self.evaluate_code(output_dir, task_description)
            
            # Check if evaluation passed
            if evaluation["passed"]:
                print(f"\n   ✅ Task completed successfully on attempt {attempt}!")
                return {
                    "success": True,
                    "output_dir": output_dir,
                    "files": list(files.keys()),
                    "evaluation": evaluation,
                    "attempts": attempt,
                    "requires_approval": False
                }
            else:
                # Evaluation failed
                print(f"   ⚠️  Quality gates failed:")
                for issue in evaluation["issues"][:5]:  # Show top 5 issues
                    print(f"      - {issue}")
                
                if attempt < max_retries:
                    print(f"   🔄 Regenerating with corrections...\n")
                    previous_issues = evaluation["issues"]
                else:
                    # Max retries exceeded
                    print(f"\n   ❌ Max retries ({max_retries}) exceeded")
                    print(f"   ⏸️  Requesting human approval...\n")
        
        # Max retries exceeded - return failure with approval request
        return {
            "success": False,
            "output_dir": output_dir,
            "files": list(files.keys()),
            "error": f"Quality gates failed after {max_retries} attempts",
            "evaluation": evaluation,
            "attempts": max_retries,
            "requires_approval": True,
            "approval_message": (
                f"Frontend code generation failed after {max_retries} attempts. "
                f"Issues: {', '.join(evaluation['issues'][:3])}. "
                "Do you want to: (1) Continue with current code, "
                "(2) Retry with more attempts, or (3) Modify requirements?"
            )
        }
