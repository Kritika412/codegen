#!/usr/bin/env python3
"""
Enhanced debug script to test GitHub Projects v2 Iterations
This will help identify why some iterations aren't being returned
"""

import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    print("❌ GITHUB_TOKEN not found in .env file")
    exit(1)

def test_iterations_enhanced():
    """Enhanced test to find ALL iterations in the hail project"""
    
    print("=" * 70)
    print("🔍 ENHANCED Testing GitHub Projects v2 Iterations for 'hail' project")
    print("=" * 70)
    
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Basic access
    print("\n1️⃣ Testing basic project access...")
    simple_query = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
                title
                number
                url
            }
        }
    }
    """
    
    response = requests.post(url, headers=headers, json={
        "query": simple_query,
        "variables": {"org": "harmoniaailabs", "number": 1}
    })
    
    if response.status_code != 200:
        print(f"❌ Failed: {response.status_code}")
        return
    
    result = response.json()
    if 'errors' in result:
        print(f"❌ GraphQL errors: {result['errors']}")
        return
    
    project = result['data']['organization']['projectV2']
    print(f"✅ Found project: {project['title']}")
    
    # Test 2: Get ALL iterations with enhanced query
    print("\n2️⃣ Fetching ALL iteration data...")
    
    enhanced_query = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                fields(first: 50) {
                    nodes {
                        __typename
                        ... on ProjectV2IterationField {
                            id
                            name
                            configuration {
                                startDay
                                duration
                                iterations {
                                    id
                                    title
                                    startDate
                                    duration
                                }
                                completedIterations {
                                    id
                                    title
                                    startDate
                                    duration
                                }
                            }
                        }
                    }
                }
                items(first: 100) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        content {
                            ... on Issue {
                                title
                                number
                            }
                            ... on DraftIssue {
                                title
                            }
                        }
                        fieldValues(first: 20) {
                            nodes {
                                __typename
                                ... on ProjectV2ItemFieldIterationValue {
                                    title
                                    startDate
                                    duration
                                    iterationId
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
    
    response = requests.post(url, headers=headers, json={
        "query": enhanced_query,
        "variables": {"org": "harmoniaailabs", "number": 1}
    })
    
    result = response.json()
    
    if 'errors' in result:
        print(f"⚠️ GraphQL errors: {result['errors']}")
    
    project_data = result.get('data', {}).get('organization', {}).get('projectV2', {})
    
    # Analyze iteration fields
    all_iterations = {}
    fields = project_data.get('fields', {}).get('nodes', [])
    
    for field in fields:
        if field and field.get('__typename') == 'ProjectV2IterationField':
            print(f"\n🔄 Found iteration field: {field.get('name')}")
            config = field.get('configuration', {})
            
            # Active iterations
            active = config.get('iterations', [])
            print(f"   📈 Active/Future iterations ({len(active)}):")
            for it in active:
                print(f"      - {it['title']}: {it.get('startDate', 'No date')}")
                all_iterations[it['id']] = {**it, 'source': 'active'}
            
            # Completed iterations  
            completed = config.get('completedIterations', [])
            print(f"   ✅ Completed iterations ({len(completed)}):")
            for it in completed:
                print(f"      - {it['title']}: {it.get('startDate', 'No date')}")
                all_iterations[it['id']] = {**it, 'source': 'completed'}
    
    # Test 3: Analyze items and their iterations
    print("\n3️⃣ Analyzing project items and their iteration assignments...")
    
    items = project_data.get('items', {}).get('nodes', [])
    print(f"Found {len(items)} items in project")
    
    item_iterations = {}
    
    for item in items:
        content = item.get('content')
        title = "Unknown"
        if content:
            title = content.get('title', 'Unknown')
            if 'number' in content:
                title = f"#{content['number']} {title}"
        
        # Find iteration assignment
        for field_value in item.get('fieldValues', {}).get('nodes', []):
            if field_value and field_value.get('__typename') == 'ProjectV2ItemFieldIterationValue':
                iteration_title = field_value.get('title')
                if iteration_title:
                    if iteration_title not in item_iterations:
                        item_iterations[iteration_title] = []
                    item_iterations[iteration_title].append(title[:50])
                    
                    # Track iteration details from items
                    iteration_id = field_value.get('iterationId', iteration_title)
                    if iteration_id not in all_iterations:
                        all_iterations[iteration_id] = {
                            'id': iteration_id,
                            'title': iteration_title,
                            'startDate': field_value.get('startDate'),
                            'duration': field_value.get('duration', 14),
                            'source': 'from_items'
                        }
    
    print(f"\n📊 Found {len(item_iterations)} iterations with assigned items:")
    for iteration_name, items_list in item_iterations.items():
        print(f"   {iteration_name}: {len(items_list)} items")
        # Show first few items
        for item_title in items_list[:3]:
            print(f"      - {item_title}")
        if len(items_list) > 3:
            print(f"      ... and {len(items_list) - 3} more")
    
    # Test 4: Summary of ALL discovered iterations
    print(f"\n4️⃣ SUMMARY: Found {len(all_iterations)} total unique iterations:")
    print("=" * 50)
    
    today = datetime.now().date()
    
    for iteration_id, iteration_data in all_iterations.items():
        title = iteration_data.get('title', 'Unknown')
        source = iteration_data.get('source', 'unknown')
        start_date = iteration_data.get('startDate')
        duration = iteration_data.get('duration', 14)
        
        status = f"[{source}]"
        date_info = "No dates"
        
        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = start + timedelta(days=duration)
                date_info = f"{start.strftime('%b %d')} - {end.strftime('%b %d')}"
                
                if start <= today <= end:
                    status += " 🟢 CURRENT"
                elif today < start:
                    status += " 🔵 FUTURE"
                else:
                    status += " ⚪ PAST"
            except:
                date_info = f"Invalid date: {start_date}"
        
        item_count = len(item_iterations.get(title, []))
        print(f"   {title} {status}")
        print(f"      📅 {date_info}")
        print(f"      📋 {item_count} items assigned")
        print()

if __name__ == "__main__":
    test_iterations_enhanced()
    print("\n" + "=" * 70)
    print("✅ Enhanced test complete!")
    print("=" * 70)