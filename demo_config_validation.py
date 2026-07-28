"""
Demonstration of the Configuration Validation System (Task 19.1).

This script demonstrates:
1. Environment variable validation
2. Configuration template generation for different environments
3. Secrets detection in generated code
4. Configuration documentation generation

**Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**
"""

import os
from pathlib import Path
from workflow.config import (
    ConfigValidator,
    ConfigTemplateGenerator,
    ConfigDocGenerator,
    Environment
)


def demo_environment_validation():
    """Demonstrate environment variable validation."""
    print("=" * 80)
    print("1. ENVIRONMENT VARIABLE VALIDATION")
    print("=" * 80)
    
    # Validate workflow environment
    print("\n✓ Validating workflow system environment variables...")
    result = ConfigValidator.validate_workflow_environment()
    print(result)
    print()


def demo_template_generation():
    """Demonstrate configuration template generation."""
    print("=" * 80)
    print("2. CONFIGURATION TEMPLATE GENERATION")
    print("=" * 80)
    
    output_dir = Path("./demo_config_output")
    output_dir.mkdir(exist_ok=True)
    
    # Generate backend templates for all environments
    print("\n✓ Generating backend configuration templates...")
    for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]:
        output_path = output_dir / f".env.backend.{env.value}"
        ConfigTemplateGenerator.generate_backend_template(
            environment=env,
            include_postgres=True,
            include_mongo=True,
            output_path=str(output_path)
        )
        print(f"  - Generated: {output_path}")
    
    # Generate frontend templates for all environments
    print("\n✓ Generating frontend configuration templates...")
    for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]:
        output_path = output_dir / f".env.frontend.{env.value}"
        ConfigTemplateGenerator.generate_frontend_template(
            environment=env,
            output_path=str(output_path)
        )
        print(f"  - Generated: {output_path}")
    
    # Generate Docker Compose templates
    print("\n✓ Generating Docker Compose templates...")
    for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]:
        output_path = output_dir / f"docker-compose.{env.value}.yml"
        ConfigTemplateGenerator.generate_docker_compose_template(
            environment=env,
            include_postgres=True,
            include_mongo=True,
            output_path=str(output_path)
        )
        print(f"  - Generated: {output_path}")
    
    print(f"\n✓ All templates generated in: {output_dir}")
    print()


def demo_secrets_scanning():
    """Demonstrate secrets detection."""
    print("=" * 80)
    print("3. SECRETS DETECTION")
    print("=" * 80)
    
    # Create demo files with and without secrets
    demo_dir = Path("./demo_secrets_scan")
    demo_dir.mkdir(exist_ok=True)
    
    # Clean code example
    clean_file = demo_dir / "clean_config.py"
    clean_file.write_text("""
import os

# Good practice - read from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")
""")
    
    # Dirty code example
    dirty_file = demo_dir / "dirty_config.py"
    dirty_file.write_text("""
# Bad practice - hardcoded credentials
DATABASE_URL = "postgresql://user:password123@localhost:5432/db"
API_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890"
SECRET_KEY = "my_super_secret_key"
""")
    
    print("\n✓ Scanning clean code (uses environment variables)...")
    result = ConfigValidator.scan_for_secrets(str(clean_file))
    if result.passed:
        print("  ✅ No secrets detected - code is secure!")
    else:
        print(f"  ❌ Found {len(result.errors)} issues")
    
    print("\n✓ Scanning dirty code (has hardcoded credentials)...")
    result = ConfigValidator.scan_for_secrets(str(dirty_file))
    if not result.passed:
        print(f"  ⚠️  Found {len(result.errors)} hardcoded secrets:")
        for error in result.errors:
            print(f"    - {error}")
    
    # Scan entire directory
    print("\n✓ Scanning entire directory...")
    result = ConfigValidator.scan_directory_for_secrets(str(demo_dir))
    print(result)
    
    # Cleanup
    import shutil
    shutil.rmtree(demo_dir)
    print()


def demo_backend_validation():
    """Demonstrate backend environment validation."""
    print("=" * 80)
    print("4. BACKEND ENVIRONMENT VALIDATION")
    print("=" * 80)
    
    # Check if backend .env exists
    backend_env = Path("./backend/.env")
    if backend_env.exists():
        print("\n✓ Validating backend environment configuration...")
        result = ConfigValidator.validate_backend_environment(str(backend_env))
        print(result)
    else:
        print("\n⚠️  Backend .env file not found (this is expected if no backend is generated)")
    print()


def demo_frontend_validation():
    """Demonstrate frontend environment validation."""
    print("=" * 80)
    print("5. FRONTEND ENVIRONMENT VALIDATION")
    print("=" * 80)
    
    # Check if frontend .env exists
    frontend_env = Path("./frontend/.env.local")
    if frontend_env.exists():
        print("\n✓ Validating frontend environment configuration...")
        result = ConfigValidator.validate_frontend_environment(str(frontend_env))
        print(result)
    else:
        print("\n⚠️  Frontend .env.local file not found (this is expected if no frontend is generated)")
    print()


def demo_documentation_generation():
    """Demonstrate configuration documentation generation."""
    print("=" * 80)
    print("6. CONFIGURATION DOCUMENTATION GENERATION")
    print("=" * 80)
    
    output_path = Path("./demo_config_output/CONFIGURATION_GUIDE.md")
    output_path.parent.mkdir(exist_ok=True)
    
    print("\n✓ Generating comprehensive configuration guide...")
    ConfigDocGenerator.generate_configuration_guide(str(output_path))
    print(f"  - Generated: {output_path}")
    print(f"  - Size: {output_path.stat().st_size} bytes")
    
    # Show preview of documentation
    print("\n✓ Documentation preview (first 20 lines):")
    print("-" * 80)
    with open(output_path, 'r') as f:
        for i, line in enumerate(f):
            if i >= 20:
                break
            print(line.rstrip())
    print("-" * 80)
    print(f"\n✓ Full documentation available at: {output_path}")
    print()


def main():
    """Run all configuration validation demonstrations."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "CONFIGURATION VALIDATION SYSTEM DEMO" + " " * 27 + "║")
    print("║" + " " * 15 + "Task 19.1 - Requirements 14.1-14.5" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        demo_environment_validation()
        demo_template_generation()
        demo_secrets_scanning()
        demo_backend_validation()
        demo_frontend_validation()
        demo_documentation_generation()
        
        print("=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print("\n✅ All configuration validation features demonstrated successfully!")
        print("\nGenerated files:")
        print("  - ./demo_config_output/.env.backend.* (3 files)")
        print("  - ./demo_config_output/.env.frontend.* (3 files)")
        print("  - ./demo_config_output/docker-compose.*.yml (3 files)")
        print("  - ./demo_config_output/CONFIGURATION_GUIDE.md")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
