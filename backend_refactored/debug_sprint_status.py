#!/usr/bin/env python3
"""
Debug script to test sprint summary status counting.

This script will help identify what status values are actually being
returned from GitHub and verify the status counting logic.
"""

import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.sprint_service import SprintService
from app.core.config import logger, Config
import logging

def test_sprint_summary_debug():
    """Test sprint summary with debug logging to see actual status values."""
    
    # Set debug logging level to see detailed status information
    logger.setLevel(logging.DEBUG)
    
    # Add console handler for debug output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    try:
        print("🔍 Testing Sprint Summary Status Counting")
        print("=" * 50)
        
        # Get a sprint name - you can modify this
        sprint_name = input("Enter sprint name (e.g., 'Sprint 34'): ").strip()
        if not sprint_name:
            sprint_name = "Sprint 34"  # Default for testing
        
        print(f"\n📊 Analyzing sprint: {sprint_name}")
        print("-" * 30)
        
        # Initialize service
        sprint_service = SprintService()
        
        # Get raw issues to see their status values
        print("\n🔍 Getting raw issues from GitHub...")
        raw_issues = sprint_service.github_service.get_project_items_by_iteration(
            sprint_name=sprint_name,
            status_filter=None
        )
        
        print(f"\n📋 Found {len(raw_issues)} total issues")
        print("\n🏷️  Raw status values found:")
        
        # Collect all unique status values
        unique_statuses = set()
        for issue in raw_issues:
            status = issue.get('status', 'Unknown')
            unique_statuses.add(status)
            print(f"  - '{status}' (original)")
            if status:
                print(f"    -> '{status.lower()}' (lowercase)")
        
        print(f"\n📊 Unique statuses: {sorted(unique_statuses)}")
        
        # Now test the sprint summary
        print(f"\n🎯 Generating sprint summary...")
        summary = sprint_service.get_sprint_summary(sprint_name)
        
        print(f"\n✅ Sprint Summary Results:")
        print(f"  Total Issues: {summary.total_issues}")
        print(f"  Backlog: {summary.backlog}")
        print(f"  Ready: {summary.ready}")
        print(f"  In Progress: {summary.in_progress}")
        print(f"  In Review: {summary.in_review}")
        
        # Verify totals add up
        counted_total = summary.backlog + summary.ready + summary.in_progress + summary.in_review
        print(f"\n🧮 Verification:")
        print(f"  Counted total: {counted_total}")
        print(f"  Expected total: {summary.total_issues}")
        print(f"  Match: {'✅' if counted_total == summary.total_issues else '❌'}")
        
        if counted_total != summary.total_issues:
            uncounted = summary.total_issues - counted_total
            print(f"  Uncounted issues: {uncounted}")
            print(f"  This suggests some statuses don't match the expected categories")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Test failed: {str(e)}", exc_info=True)

def main():
    """Main entry point."""
    print("Sprint Summary Debug Tool")
    print("This tool helps debug status counting issues")
    print()
    
    # Validate configuration
    try:
        Config.validate()
        print("✅ Configuration validated")
    except Exception as e:
        print(f"❌ Configuration error: {str(e)}")
        return
    
    test_sprint_summary_debug()

if __name__ == "__main__":
    main()
