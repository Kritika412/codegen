#!/usr/bin/env python3
"""
Debug script to test what the UI is calling and compare results.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_api_calls():
    """Test the API calls that the UI might be making."""
    
    base_url = "http://localhost:8000"
    
    # Test different sprint summary calls
    test_cases = [
        "/api/sprint-summary?sprint_name=Sprint%201",
        "/api/sprints/summary?sprint_name=Sprint%201", 
        "/api/sprint-summary?sprint_name=Sprint%202",
        "/api/sprints/summary?sprint_name=Sprint%202",
    ]
    
    print("🔍 Testing API Endpoints")
    print("=" * 50)
    
    for endpoint in test_cases:
        print(f"\n📡 Testing: {endpoint}")
        try:
            response = requests.get(f"{base_url}{endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'total_issues' in data:
                    print(f"   Total Issues: {data['total_issues']}")
                    print(f"   Backlog: {data.get('backlog', 'N/A')}")
                    print(f"   Ready: {data.get('ready', 'N/A')}")
                    print(f"   In Progress: {data.get('in_progress', 'N/A')}")
                    print(f"   In Review: {data.get('in_review', 'N/A')}")
                else:
                    print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            else:
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    # Test issues endpoint
    print(f"\n📡 Testing Issues Endpoint")
    issues_tests = [
        "/api/issues?sprint_name=Sprint%201",
        "/api/issues/?sprint_name=Sprint%201",
        "/api/issues?sprint_name=Sprint%202", 
    ]
    
    for endpoint in issues_tests:
        print(f"\n📋 Testing: {endpoint}")
        try:
            response = requests.get(f"{base_url}{endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Issues Count: {len(data)}")
                if data:
                    # Show status breakdown
                    statuses = {}
                    for issue in data:
                        status = issue.get('status', 'Unknown')
                        statuses[status] = statuses.get(status, 0) + 1
                    print(f"   Status Breakdown: {statuses}")
            else:
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   Exception: {e}")

if __name__ == "__main__":
    test_api_calls()
