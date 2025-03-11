import requests
import json

def test_orcid_api():
    orcid_id = "0000-0002-2685-2637"
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    headers = {
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Print the structure of the response
        print(f"Keys in response: {list(data.keys())}")
        
        # Check if 'group' exists
        if 'group' in data:
            works = data.get('group', [])
            print(f"Found {len(works)} works")
            
            # Print first work details
            if works:
                work = works[0]
                print(f"Keys in work: {list(work.keys())}")
                
                if 'work-summary' in work:
                    work_summary = work.get('work-summary', [{}])[0]
                    print(f"Keys in work_summary: {list(work_summary.keys())}")
                    
                    # Try to extract title
                    title = work_summary.get('title', {})
                    print(f"Title structure: {title}")
                    
                    title_value = title.get('title', {}).get('value')
                    print(f"Title value: {title_value}")
                else:
                    print("No 'work-summary' key found")
        else:
            print("No 'group' key found in response")
            print(f"Available keys: {list(data.keys())}")
            
            # If 'works' key exists, try that instead
            if 'works' in data:
                works = data.get('works', {})
                print(f"Found 'works' key with type: {type(works)}")
                print(f"Content of 'works': {works}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_orcid_api()