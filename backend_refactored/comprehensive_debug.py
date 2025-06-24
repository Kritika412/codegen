#!/usr/bin/env python3
"""
Comprehensive debug script to understand the UI issue.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def debug_sprint_data():
    """Debug what sprint data is actually returned."""
    
    base_url = "http://localhost:8000"
    
    print("🔍 COMPREHENSIVE API DEBUG")
    print("=" * 60)
    
    # Test all available sprints first
    print("\\n1️⃣ GETTING ALL AVAILABLE SPRINTS")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/api/sprints")
        if response.status_code == 200:
            sprints = response.json()
            print(f"Found {len(sprints)} sprints:")
            for sprint in sprints:
                print(f"   - {sprint['name']} (ID: {sprint['id']})")
        else:
            print(f"Error getting sprints: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception getting sprints: {e}")
    
    # Test specific sprint summaries  
    sprints_to_test = ["Sprint 1", "Sprint 2", "Sprint 34"]
    
    for sprint_name in sprints_to_test:
        print(f"\\n2️⃣ TESTING SPRINT: {sprint_name}")
        print("-" * 40)
        
        # Test both endpoints
        endpoints = [
            f"/api/sprint-summary?sprint_name={sprint_name.replace(' ', '%20')}",
            f"/api/sprints/summary?sprint_name={sprint_name.replace(' ', '%20')}"
        ]
        
        for endpoint in endpoints:
            print(f"\\n📡 Testing: {endpoint}")
            try:
                response = requests.get(f"{base_url}{endpoint}")
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ RESULTS:")
                    print(f"      Sprint: {data.get('current_sprint', 'N/A')}")
                    print(f"      Total: {data.get('total_issues', 'N/A')}")
                    print(f"      Backlog: {data.get('backlog', 'N/A')}")
                    print(f"      Ready: {data.get('ready', 'N/A')}")
                    print(f"      In Progress: {data.get('in_progress', 'N/A')}")
                    print(f"      In Review: {data.get('in_review', 'N/A')}")
                    print(f"      Days Remaining: {data.get('days_remaining', 'N/A')}")
                else:
                    print(f"   ❌ Error: {response.text}")
                    
            except Exception as e:
                print(f"   💥 Exception: {e}")
        
        # Test issues endpoint for this sprint
        print(f"\\n📋 Testing Issues for {sprint_name}")
        try:
            issues_url = f"{base_url}/api/issues?sprint_name={sprint_name.replace(' ', '%20')}"
            response = requests.get(issues_url)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                issues = response.json()
                print(f"   Issues Count: {len(issues)}")
                
                # Status breakdown
                statuses = {}
                for issue in issues:
                    status = issue.get('status', 'Unknown')
                    statuses[status] = statuses.get(status, 0) + 1
                
                print(f"   Status Breakdown: {statuses}")
                
                # Show first few issues
                print(f"   Sample Issues:")
                for i, issue in enumerate(issues[:3]):
                    title = issue.get('title', 'No title')[:50]
                    status = issue.get('status', 'Unknown')
                    print(f"      {i+1}. {title} -> {status}")
                    
            else:
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    # Test ready issues endpoint
    print(f"\\n3️⃣ TESTING READY ISSUES ENDPOINT")
    print("-" * 40)
    
    for sprint_name in ["Sprint 1"]:
        try:
            ready_url = f"{base_url}/api/issues/ready?sprint_name={sprint_name.replace(' ', '%20')}"
            print(f"\\n📡 Testing: {ready_url}")
            response = requests.get(ready_url)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                ready_issues = response.json()
                print(f"   ✅ Found {len(ready_issues)} ready issues")
                for issue in ready_issues:
                    title = issue.get('title', 'No title')[:50]
                    status = issue.get('status', 'Unknown')
                    print(f"      - {title} (Status: {status})")
            else:
                print(f"   ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"   💥 Exception: {e}")

if __name__ == "__main__":
    print("Please make sure the refactored API server is running at http://localhost:8000")
    print("Run: ./run.sh in the backend_refactored directory")
    print()
    
    try:
        # Quick health check
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!")
            debug_sprint_data()
        else:
            print("❌ Server responded but not healthy")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please start the server first with: ./run.sh")
