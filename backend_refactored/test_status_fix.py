#!/usr/bin/env python3
"""
Test script to verify the fixed sprint summary status counting.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
org = 'harmoniaailabs'
project_number = 5

def normalize_text(text):
    """Normalize text by replacing unicode dashes and normalizing characters"""
    import unicodedata
    text = text.replace('–', '-').replace('—', '-')
    text = unicodedata.normalize('NFKD', text)
    return text.strip()

def extract_sprint_number(sprint_name):
    """Extract sprint number from sprint name like 'Sprint 1', 'Sprint 2', etc."""
    import re
    match = re.match(r"Sprint\s+(\d+)", sprint_name, re.IGNORECASE)
    return match.group(1) if match else None

def get_project_items_by_iteration(sprint_name):
    """Get project items for a specific sprint - simplified version."""
    
    url = "https://api.github.com/graphql"
    
    # Extract sprint number
    sprint_number = extract_sprint_number(sprint_name)
    if not sprint_number:
        raise Exception(f"Could not extract sprint number from '{sprint_name}'")
    
    expected_iteration = f"Iteration {sprint_number}"
    
    # Get project ID
    query_project = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
            }
        }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query_project,
        "variables": {
            "org": org,
            "number": project_number
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    
    project_id = result['data']['organization']['projectV2']['id']
    
    # Get project items
    query_items = """
    query($projectId: ID!) {
        node(id: $projectId) {
            ... on ProjectV2 {
                items(first: 100) {
                    nodes {
                        id
                        content {
                            ... on Issue {
                                number
                                title
                            }
                            ... on DraftIssue {
                                title
                            }
                        }
                        fieldValues(first: 10) {
                            nodes {
                                ... on ProjectV2ItemFieldSingleSelectValue {
                                    name
                                    field {
                                        ... on ProjectV2SingleSelectField {
                                            name
                                        }
                                    }
                                }
                                ... on ProjectV2ItemFieldIterationValue {
                                    title
                                    field {
                                        ... on ProjectV2IterationField {
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    data = {
        "query": query_items,
        "variables": {"projectId": project_id}
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    items_result = response.json()
    
    items = items_result['data']['node']['items']['nodes']
    
    # Filter by iteration and extract status
    filtered_issues = []
    
    for item in items:
        if not item.get('content'):
            continue
        
        field_values = item.get('fieldValues', {}).get('nodes', [])
        iteration_title = None
        status = None
        
        for field_value in field_values:
            if 'field' in field_value and field_value['field']:
                field_name = field_value['field'].get('name', '').lower()
                
                if 'title' in field_value:
                    iteration_title = normalize_text(field_value.get('title', ''))
                
                if field_name == 'status':
                    status = field_value.get('name')
        
        # Check if item belongs to the expected iteration
        if iteration_title == normalize_text(expected_iteration):
            filtered_issues.append({
                'content': item['content'],
                'status': status or 'Unknown'
            })
    
    return filtered_issues

def calculate_status_counts_original_style(issues):
    """Calculate status counts using the original logic."""
    status_counts = {
        'backlog': 0,
        'ready': 0,
        'in progress': 0,
        'in review': 0,
        'total': len(issues)
    }
    
    for issue in issues:
        status = issue['status'].lower() if issue['status'] else 'unknown'
        if status in status_counts:
            status_counts[status] += 1
    
    return status_counts

def main():
    """Test the status counting with actual data."""
    
    print("🧪 Testing Sprint Summary Status Counting")
    print("=" * 50)
    
    # Test with Iteration 1 (which has data according to our check)
    sprint_name = "Sprint 1"
    
    try:
        print(f"📊 Getting issues for: {sprint_name}")
        issues = get_project_items_by_iteration(sprint_name)
        
        print(f"📋 Found {len(issues)} issues in {sprint_name}")
        
        # Show each issue's status
        print("\\n📝 Issue details:")
        for i, issue in enumerate(issues, 1):
            title = issue['content'].get('title', 'No title')[:50]
            status = issue['status']
            print(f"  {i}. {title} -> Status: '{status}' (lowercase: '{status.lower()}')")
        
        # Calculate status counts
        print("\\n🧮 Calculating status counts...")
        status_counts = calculate_status_counts_original_style(issues)
        
        print(f"\\n✅ Status Count Results:")
        print(f"  Total Issues: {status_counts['total']}")
        print(f"  Backlog: {status_counts['backlog']}")
        print(f"  Ready: {status_counts['ready']}")
        print(f"  In Progress: {status_counts['in progress']}")
        print(f"  In Review: {status_counts['in review']}")
        
        # Verify totals
        counted_total = (status_counts['backlog'] + status_counts['ready'] + 
                        status_counts['in progress'] + status_counts['in review'])
        
        print(f"\\n🔍 Verification:")
        print(f"  Sum of categories: {counted_total}")
        print(f"  Total issues: {status_counts['total']}")
        print(f"  Match: {'✅' if counted_total == status_counts['total'] else '❌'}")
        
        if counted_total != status_counts['total']:
            uncounted = status_counts['total'] - counted_total
            print(f"  ⚠️  Uncounted issues: {uncounted}")
            print(f"     This indicates issues with statuses not in the expected categories")
        
        print(f"\\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"\\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not found in environment")
        exit(1)
    
    main()
