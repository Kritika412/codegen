#!/usr/bin/env python3
"""
Simple script to check what status values are actually returned from GitHub API.
This will help us debug the status counting issue.
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

def get_sample_project_items():
    """Get a sample of project items to see what status values exist."""
    
    url = "https://api.github.com/graphql"
    
    # First get project ID
    query_project = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
                title
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
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if 'errors' in result:
            print(f"GraphQL errors: {result['errors']}")
            return
            
        project_id = result['data']['organization']['projectV2']['id']
        print(f"Project ID: {project_id}")
        
        # Now get some items
        query_items = """
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: 20) {
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
                                    ... on ProjectV2ItemFieldTextValue {
                                        text
                                        field {
                                            ... on ProjectV2Field {
                                                name
                                            }
                                        }
                                    }
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
        
        if 'errors' in items_result:
            print(f"GraphQL errors: {items_result['errors']}")
            return
            
        items = items_result['data']['node']['items']['nodes']
        print(f"\\nFound {len(items)} project items")
        
        # Extract all status values
        status_values = set()
        iteration_values = set()
        
        for item in items:
            if not item.get('content'):
                continue
                
            print(f"\\n--- Item: {item['content'].get('title', 'No title')[:50]} ---")
            
            field_values = item.get('fieldValues', {}).get('nodes', [])
            item_status = None
            item_iteration = None
            
            for field_value in field_values:
                if 'field' in field_value and field_value['field']:
                    field_name = field_value['field'].get('name', '')
                    print(f"  Field: {field_name}")
                    
                    if field_name.lower() == 'status':
                        status = field_value.get('name') or field_value.get('text')
                        print(f"    Status: '{status}'")
                        if status:
                            status_values.add(status)
                            item_status = status
                    
                    if 'title' in field_value:
                        iteration = field_value.get('title')
                        print(f"    Iteration: '{iteration}'")
                        if iteration:
                            iteration_values.add(iteration)
                            item_iteration = iteration
            
            print(f"  -> Status: {item_status}, Iteration: {item_iteration}")
        
        print(f"\\n=== SUMMARY ===")
        print(f"Unique Status Values Found:")
        for status in sorted(status_values):
            print(f"  - '{status}' -> lowercase: '{status.lower()}'")
            
        print(f"\\nUnique Iteration Values Found:")
        for iteration in sorted(iteration_values):
            print(f"  - '{iteration}'")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not found in environment")
        exit(1)
    
    print("🔍 Checking GitHub Project Status Values")
    print("=" * 50)
    get_sample_project_items()
