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
        works = data.get('group', [])
        
        print(f"Found {len(works)} works")
        
        # Check first work for author information
        if works:
            work = works[0]
            print("\nExamining first work:")
            
            # Check work summary for author information
            work_summary = work.get('work-summary', [{}])[0]
            print(f"Work summary keys: {list(work_summary.keys())}")
            
            # Check if contributors exist
            if 'contributors' in work_summary:
                print("\nContributors found!")
                contributors = work_summary.get('contributors')
                print(f"Contributors structure: {contributors}")
            else:
                print("\nNo contributors in work_summary")
            
            # Need to fetch the full work record to get contributors
            if 'put-code' in work_summary:
                put_code = work_summary.get('put-code')
                print(f"\nFetching full work details for put-code: {put_code}")
                
                detail_url = f"https://pub.orcid.org/v3.0/{orcid_id}/work/{put_code}"
                detail_response = requests.get(detail_url, headers=headers)
                detail_response.raise_for_status()
                
                work_detail = detail_response.json()
                print(f"Work detail keys: {list(work_detail.keys())}")
                
                # Check for contributors in full work record
                if 'contributors' in work_detail:
                    contributors = work_detail.get('contributors')
                    print(f"\nContributors found in detail record!")
                    print(f"Contributors keys: {list(contributors.keys())}")
                    
                    if 'contributor' in contributors:
                        contributor_list = contributors.get('contributor', [])
                        print(f"Found {len(contributor_list)} contributors")
                        
                        # Print first 3 contributors
                        for i, contributor in enumerate(contributor_list[:3]):
                            print(f"\nContributor {i+1}:")
                            print(f"Contributor keys: {list(contributor.keys())}")
                            
                            credit_name = contributor.get('credit-name', {}).get('value', 'Unknown')
                            print(f"Credit name: {credit_name}")
                            
                            # Check if there's contributor attributes
                            if 'contributor-attributes' in contributor:
                                attrs = contributor.get('contributor-attributes')
                                print(f"Contributor attributes: {attrs}")
                            
                            # Check for ORCID iD
                            if 'contributor-orcid' in contributor:
                                orcid_info = contributor.get('contributor-orcid', {})
                                print(f"ORCID info: {orcid_info}")
                else:
                    print("No contributors in work detail record")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_orcid_api()