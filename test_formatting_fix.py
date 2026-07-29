#!/usr/bin/env python3
"""
Quick test to verify Frontend Agent formatting fix is working.
This script checks if the formatting instructions are in the system prompt.
"""

from workflow.agents.frontend_agent import FrontendAgent

def test_formatting_instructions():
    """Test that formatting instructions are in the system prompt."""
    agent = FrontendAgent()
    
    # Get the generation system prompt
    prompt = agent._get_generation_system_prompt()
    
    # Check for key formatting phrases
    formatting_checks = [
        "CODE FORMATTING REQUIREMENTS",
        "properly formatted and readable",
        "DO NOT minify or uglify",
        "proper indentation",
        "line breaks",
        "WRONG (minified/single-line)",
        "CORRECT (properly formatted)"
    ]
    
    print("Testing Frontend Agent Formatting Fix...")
    print("=" * 60)
    
    all_passed = True
    for check in formatting_checks:
        if check in prompt:
            print(f"✅ Found: '{check}'")
        else:
            print(f"❌ Missing: '{check}'")
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ All formatting instructions present!")
        print("Frontend Agent will generate properly formatted code.")
    else:
        print("❌ Some formatting instructions missing!")
        print("Fix may not work correctly.")
    
    return all_passed


def test_regeneration_formatting():
    """Test that regeneration prompt includes formatting fixes."""
    agent = FrontendAgent()
    
    # Get the regeneration system prompt
    prompt = agent._get_regeneration_system_prompt()
    
    # Check for formatting in common issues
    formatting_checks = [
        "PROPER CODE FORMATTING",
        "Minified/single-line code",
        "Reformat with proper indentation",
        "readable, not minified"
    ]
    
    print("\nTesting Frontend Agent Regeneration Fix...")
    print("=" * 60)
    
    all_passed = True
    for check in formatting_checks:
        if check in prompt:
            print(f"✅ Found: '{check}'")
        else:
            print(f"❌ Missing: '{check}'")
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ Regeneration prompt includes formatting fixes!")
    else:
        print("❌ Some formatting fixes missing from regeneration!")
    
    return all_passed


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FRONTEND FORMATTING FIX VERIFICATION")
    print("=" * 60 + "\n")
    
    test1 = test_formatting_instructions()
    test2 = test_regeneration_formatting()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ ALL TESTS PASSED - Frontend formatting fix is working!")
    else:
        print("❌ SOME TESTS FAILED - Review the fix implementation")
    print("=" * 60 + "\n")
