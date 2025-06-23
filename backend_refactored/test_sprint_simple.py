#!/usr/bin/env python3
"""
Simple test script to check sprint summary functionality.
"""

import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.sprint_service import SprintService
from app.core.config import logger, Config
import logging

def test_sprint_summary():
    """Test sprint summary with a known sprint."""
    
    try:
        print("🔍 Testing Sprint Summary")
        print("=" * 30)
        
        # Set up debug logging to see what's happening
        logger.setLevel(logging.DEBUG)
        
        # Use a Sprint name - adjust this to match your actual sprints
        sprint_name = "Sprint 34"  # Change this to a real sprint name
        
        print(f"📊 Testing sprint: {sprint_name}")
        
        # Initialize service
        sprint_service = SprintService()
        
        # First, let's see what sprints are available
        print("\n📋 Available sprints:")
        try:
            sprints = sprint_service.get_all_sprints()
            for sprint in sprints[:5]:  # Show first 5
                print(f"  - {sprint.name}")
            
            if sprints:
                # Use the first available sprint
                sprint_name = sprints[0].name
                print(f"\n🎯 Using sprint: {sprint_name}")
        except Exception as e:
            print(f"⚠️  Could not get sprints: {e}")
        
        # Get sprint summary
        print(f"\n📊 Getting summary for: {sprint_name}")
        summary = sprint_service.get_sprint_summary(sprint_name)
        
        print(f"\n✅ Results:")
        print(f"  Total Issues: {summary.total_issues}")
        print(f"  Backlog: {summary.backlog}")
        print(f"  Ready: {summary.ready}")
        print(f"  In Progress: {summary.in_progress}")
        print(f"  In Review: {summary.in_review}")
        
        # Check if counts add up
        counted = summary.backlog + summary.ready + summary.in_progress + summary.in_review
        print(f"\n🧮 Verification:")
        print(f"  Sum of categories: {counted}")
        print(f"  Total issues: {summary.total_issues}")
        print(f"  Match: {'✅' if counted == summary.total_issues else '❌'}")
        
        if counted != summary.total_issues:
            print(f"  🔍 Missing: {summary.total_issues - counted} issues not categorized")
        
        return summary.total_issues > 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    try:
        Config.validate()
        print("✅ Configuration validated")
    except Exception as e:
        print(f"❌ Configuration error: {str(e)}")
        return
    
    success = test_sprint_summary()
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")

if __name__ == "__main__":
    main()
