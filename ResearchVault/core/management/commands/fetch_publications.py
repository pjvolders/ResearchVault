import requests
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Publication, Person
from django.db import transaction
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches publications from various sources and adds them to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Specify the source to fetch from: scopus, pubmed, crossref, orcid, or all',
            default='all'
        )
        parser.add_argument(
            '--author',
            type=str,
            help='Specify author name to search for',
        )
        parser.add_argument(
            '--orcid',
            type=str,
            help='Specify ORCID ID to search for',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing',
        )

    def handle(self, *args, **options):
        source = options['source'].lower()
        author = options['author']
        orcid = options['orcid']
        dry_run = options['dry_run']

        self.stdout.write(self.style.NOTICE(f"Fetching publications from {source}..."))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made to the database"))
        
        if source == 'all' or source == 'orcid':
            if orcid:
                self.fetch_from_orcid(orcid, dry_run)
            else:
                self.stdout.write(self.style.WARNING("ORCID ID required for ORCID source"))
        
        if source == 'all' or source == 'pubmed':
            if author:
                self.fetch_from_pubmed(author, dry_run)
            else:
                self.stdout.write(self.style.WARNING("Author name required for PubMed source"))
                
        if source == 'all' or source == 'crossref':
            if author:
                self.fetch_from_crossref(author, dry_run)
            else:
                self.stdout.write(self.style.WARNING("Author name required for Crossref source"))
        
        if source == 'all' or source == 'scopus':
            self.stdout.write(self.style.WARNING("Scopus API requires an API key and institutional subscription"))
            self.stdout.write(self.style.WARNING("To set up Scopus integration, add your API key to settings.py"))
            
        self.stdout.write(self.style.SUCCESS("Fetching complete!"))
    
    def fetch_from_orcid(self, orcid_id, dry_run=False):
        """
        Fetch publications from ORCID
        """
        self.stdout.write("Fetching from ORCID...")
        
        try:
            # ORCID API base URL
            url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
            headers = {
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            works = data.get('group', [])
            
            self.stdout.write(f"Found {len(works)} works in ORCID")
            
            if dry_run:
                for work in works[:5]:  # Show first 5 in dry run
                    work_summary = work.get('work-summary', [{}])[0]
                    title_container = work_summary.get('title', {})
                    title = None
                    if title_container and 'title' in title_container:
                        title = title_container.get('title', {}).get('value', 'No title')
                    else:
                        title = 'No title available'
                    self.stdout.write(f"  Would import: {title}")
                return
            
            # Debug: print a sample work
            if works:
                self.stdout.write(self.style.WARNING("Sample work structure (debug):"))
                self.stdout.write(str(works[0].keys() if works[0] else "Empty work"))
                if 'work-summary' in works[0]:
                    self.stdout.write(str(works[0]['work-summary'][0].keys() if works[0]['work-summary'] else "Empty summary"))
            
            for work in works:
                try:
                    # Safely extract work_summary
                    if not work or not isinstance(work, dict):
                        self.stdout.write(self.style.WARNING("  Skipping invalid work entry (not a dict)"))
                        continue
                        
                    work_summaries = work.get('work-summary')
                    if not work_summaries or not isinstance(work_summaries, list) or len(work_summaries) == 0:
                        self.stdout.write(self.style.WARNING("  Skipping work with no work-summary list"))
                        continue
                        
                    work_summary = work_summaries[0]
                    if not work_summary or not isinstance(work_summary, dict):
                        self.stdout.write(self.style.WARNING("  Skipping work with invalid work_summary"))
                        continue
                    
                    # Extract publication info
                    title_container = work_summary.get('title')
                    if not title_container or not isinstance(title_container, dict):
                        self.stdout.write(self.style.WARNING("  Skipping work with missing title container"))
                        continue
                        
                    title_obj = title_container.get('title')
                    if not title_obj or not isinstance(title_obj, dict):
                        self.stdout.write(self.style.WARNING("  Skipping work with missing title object"))
                        continue
                        
                    title = title_obj.get('value')
                    if not title:
                        self.stdout.write(self.style.WARNING("  Skipping work with no title value"))
                        continue
                    
                    # Try to get journal title if available
                    journal = ''
                    journal_title = work_summary.get('journal-title')
                    if journal_title and isinstance(journal_title, dict) and 'value' in journal_title:
                        journal = journal_title.get('value', '')
                    
                    # Extract DOI if available
                    doi = None
                    external_ids_container = work_summary.get('external-ids')
                    if external_ids_container and isinstance(external_ids_container, dict):
                        external_ids = external_ids_container.get('external-id', [])
                        if external_ids and isinstance(external_ids, list):
                            for ext_id in external_ids:
                                if ext_id and isinstance(ext_id, dict) and ext_id.get('external-id-type') == 'doi':
                                    doi = ext_id.get('external-id-value')
                                    break
                    
                    # Check if publication already exists
                    if doi:
                        if Publication.objects.filter(doi=doi).exists():
                            self.stdout.write(f"  Skipping existing publication with DOI: {doi}")
                            continue
                    elif Publication.objects.filter(title=title).exists():
                        self.stdout.write(f"  Skipping existing publication with title: {title}")
                        continue
                    
                    # Create publication
                    with transaction.atomic():
                        pub = Publication()
                        pub.title = title
                        
                        # Set journal if available
                        if journal:
                            pub.journal = journal
                            
                        # Set publication date if available
                        pub_date = work_summary.get('publication-date')
                        if pub_date and isinstance(pub_date, dict):
                            # Safe extraction of date components
                            year_val = None
                            month_val = '01'
                            day_val = '01'
                            
                            year_container = pub_date.get('year')
                            if year_container and isinstance(year_container, dict):
                                year_val = year_container.get('value')
                                
                            month_container = pub_date.get('month')
                            if month_container and isinstance(month_container, dict):
                                month_val = month_container.get('value', '01')
                                
                            day_container = pub_date.get('day')
                            if day_container and isinstance(day_container, dict):
                                day_val = day_container.get('value', '01')
                            
                            if year_val:
                                try:
                                    pub.publication_year = int(year_val)
                                    # Create a full date if we have year
                                    try:
                                        pub.publication_date = timezone.datetime(
                                            int(year_val), 
                                            int(month_val) if month_val and month_val.isdigit() else 1, 
                                            int(day_val) if day_val and day_val.isdigit() else 1
                                        ).date()
                                    except (ValueError, TypeError) as e:
                                        self.stdout.write(self.style.WARNING(f"  Invalid date format: {str(e)}"))
                                        pub.publication_date = None
                                except (ValueError, TypeError) as e:
                                    self.stdout.write(self.style.WARNING(f"  Invalid year format: {year_val} - {str(e)}"))
                        
                        # Set type if available
                        work_type = work_summary.get('type')
                        if work_type:
                            pub.notes = f"Type: {work_type}"
                                
                        # Set DOI if available
                        if doi:
                            pub.doi = doi
                            
                        # Set URL if available
                        url_obj = work_summary.get('url')
                        if url_obj and isinstance(url_obj, dict) and 'value' in url_obj:
                            pub.url = url_obj.get('value')
                        
                        # Save the publication
                        pub.save()
                        
                        # Create main author link - assume the ORCID ID belongs to a person
                        try:
                            person, created = Person.objects.get_or_create(
                                orcid=orcid_id,
                                defaults={'first_name': 'Unknown', 'last_name': 'Author'}
                            )
                            pub.authors.add(person)
                            
                            # If this is the corresponding author, set it
                            pub.corresponding_author = person
                            pub.save()
                            
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"  Error adding main author: {str(e)}"))
                            
                        # Fetch detailed work record to get contributors
                        try:
                            if 'put-code' in work_summary:
                                put_code = work_summary.get('put-code')
                                self.stdout.write(f"  Fetching contributors for put-code: {put_code}")
                                
                                detail_url = f"https://pub.orcid.org/v3.0/{orcid_id}/work/{put_code}"
                                detail_response = requests.get(detail_url, headers=headers)
                                detail_response.raise_for_status()
                                
                                work_detail = detail_response.json()
                                
                                # Process contributors if available
                                if 'contributors' in work_detail and 'contributor' in work_detail.get('contributors', {}):
                                    contributors = work_detail['contributors'].get('contributor', [])
                                    self.stdout.write(f"  Found {len(contributors)} contributors")
                                    
                                    added_contributors = 0
                                    # Clear existing author orders
                                    pub.authororder_set.all().delete()
                                    
                                    for i, contributor in enumerate(contributors):
                                        # Skip if no credit name
                                        if not contributor.get('credit-name') or not contributor['credit-name'].get('value'):
                                            continue
                                            
                                        credit_name = contributor['credit-name'].get('value')
                                        
                                        # Extract first and last name
                                        name_parts = credit_name.split(' ')
                                        if len(name_parts) > 1:
                                            first_name = ' '.join(name_parts[:-1])
                                            last_name = name_parts[-1]
                                        else:
                                            first_name = ''
                                            last_name = credit_name
                                        
                                        # Check for contributor ORCID
                                        contributor_orcid = None
                                        if 'contributor-orcid' in contributor and contributor['contributor-orcid'] and 'path' in contributor['contributor-orcid']:
                                            contributor_orcid = contributor['contributor-orcid'].get('path')
                                        
                                        # Create or get person record
                                        try:
                                            # If we have ORCID, use that as primary key
                                            if contributor_orcid:
                                                co_person, created = Person.objects.get_or_create(
                                                    orcid=contributor_orcid,
                                                    defaults={
                                                        'first_name': first_name,
                                                        'last_name': last_name
                                                    }
                                                )
                                            else:
                                                # Otherwise try to match by name
                                                co_person, created = Person.objects.get_or_create(
                                                    first_name=first_name,
                                                    last_name=last_name
                                                )
                                                
                                            # Add to publication authors with correct order
                                            from core.models import AuthorOrder
                                            
                                            # Determine contribution type
                                            contribution_type = 'normal'
                                            
                                            # Check if this is a corresponding author
                                            if ('contributor-attributes' in contributor and 
                                                contributor['contributor-attributes'] and 
                                                contributor['contributor-attributes'].get('contributor-role') == 'corresponding'):
                                                contribution_type = 'corresponding'
                                                pub.corresponding_author = co_person
                                                pub.save()
                                            
                                            # Set first and last author contribution types
                                            # First author
                                            if i == 0:
                                                contribution_type = 'first'
                                            # Last author
                                            elif i == len(contributors) - 1:
                                                contribution_type = 'last'
                                            
                                            # Create author order with contribution type
                                            AuthorOrder.objects.create(
                                                publication=pub,
                                                person=co_person,
                                                order=i,  # Order is the index in the contributors list
                                                contribution_type=contribution_type
                                            )
                                            added_contributors += 1
                                                    
                                        except Exception as e:
                                            self.stdout.write(self.style.ERROR(f"  Error adding contributor {credit_name}: {str(e)}"))
                                    
                                    self.stdout.write(f"  Added {added_contributors} co-authors")
                                    pub.save()
                                else:
                                    self.stdout.write("  No contributors found in work detail")
                                    
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"  Error fetching contributors: {str(e)}"))
                        
                        self.stdout.write(self.style.SUCCESS(f"  Added publication: {title}"))
                except Exception as e:
                    import traceback
                    self.stdout.write(self.style.ERROR(f"  Error processing work: {str(e)}"))
                    self.stdout.write(self.style.ERROR(traceback.format_exc()))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching from ORCID: {str(e)}"))
    
    def fetch_from_pubmed(self, author_name, dry_run=False):
        """
        Fetch publications from PubMed
        """
        self.stdout.write("Fetching from PubMed...")
        
        try:
            # PubMed E-utilities API
            # First search for the author
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                'db': 'pubmed',
                'term': f"{author_name}[Author]",
                'retmode': 'json',
                'retmax': 100  # Limit to 100 results
            }
            
            search_response = requests.get(search_url, params=search_params)
            search_response.raise_for_status()
            
            search_data = search_response.json()
            pmids = search_data.get('esearchresult', {}).get('idlist', [])
            
            if not pmids:
                self.stdout.write("No PubMed articles found for this author")
                return
                
            self.stdout.write(f"Found {len(pmids)} articles in PubMed")
            
            if dry_run:
                self.stdout.write(f"  Would fetch details for {min(5, len(pmids))} articles")
                return
            
            # Fetch details for each article
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(pmids),
                'retmode': 'xml'
            }
            
            fetch_response = requests.get(fetch_url, params=fetch_params)
            fetch_response.raise_for_status()
            
            # Parse XML response - this would typically use xml.etree.ElementTree
            # For simplicity, we'll just count how many we'd process
            xml_content = fetch_response.text
            self.stdout.write(f"Retrieved XML data for {len(pmids)} articles")
            self.stdout.write(f"PubMed integration requires XML parsing implementation")
            self.stdout.write(f"For a full implementation, XML parsing code would be added here")
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching from PubMed: {str(e)}"))
    
    def fetch_from_crossref(self, author_name, dry_run=False):
        """
        Fetch publications from Crossref
        """
        self.stdout.write("Fetching from Crossref...")
        
        try:
            # Crossref API for querying works
            url = "https://api.crossref.org/works"
            params = {
                'query.author': author_name,
                'rows': 20,  # Limit to 20 results for demo
                'sort': 'published',
                'order': 'desc'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('message', {}).get('items', [])
            
            self.stdout.write(f"Found {len(items)} works in Crossref")
            
            if dry_run:
                for item in items[:5]:  # Show first 5 in dry run
                    title = item.get('title', ['No title'])[0]
                    self.stdout.write(f"  Would import: {title}")
                return
            
            for item in items:
                # Extract basic info
                try:
                    title = item.get('title', [''])[0]
                    if not title:
                        continue
                        
                    doi = item.get('DOI')
                    
                    # Check if publication already exists
                    if doi and Publication.objects.filter(doi=doi).exists():
                        self.stdout.write(f"  Skipping existing publication with DOI: {doi}")
                        continue
                    elif Publication.objects.filter(title=title).exists():
                        self.stdout.write(f"  Skipping existing publication with title: {title}")
                        continue
                    
                    # Create publication
                    with transaction.atomic():
                        pub = Publication()
                        pub.title = title
                        
                        # Get publication date
                        published_date = item.get('published-print', item.get('published-online'))
                        if published_date:
                            date_parts = published_date.get('date-parts', [[]])[0]
                            if len(date_parts) >= 1:
                                pub.publication_year = date_parts[0]
                                
                                # Create full date if we have all parts
                                if len(date_parts) >= 3:
                                    try:
                                        pub.publication_date = timezone.datetime(
                                            date_parts[0], date_parts[1], date_parts[2]
                                        ).date()
                                    except (ValueError, TypeError):
                                        pub.publication_date = None
                        
                        # Set journal info
                        container = item.get('container-title', [''])[0]
                        if container:
                            pub.journal = container
                            
                        # Set page info
                        if 'page' in item:
                            pub.pages = item['page']
                            
                        # Set volume/issue
                        if 'volume' in item:
                            pub.volume = item['volume']
                        if 'issue' in item:
                            pub.issue = item['issue']
                            
                        # Set DOI
                        if doi:
                            pub.doi = doi
                            
                        # Set abstract if available
                        if 'abstract' in item:
                            pub.abstract = item['abstract']
                            
                        # Set URL
                        if 'URL' in item:
                            pub.url = item['URL']
                            
                        # Save the publication
                        pub.save()
                        
                        # Add authors
                        authors_data = item.get('author', [])
                        for author_data in authors_data:
                            given = author_data.get('given', '')
                            family = author_data.get('family', '')
                            
                            if not family:  # Skip if no family name
                                continue
                                
                            # Try to match existing Person or create new one
                            try:
                                person, created = Person.objects.get_or_create(
                                    first_name=given,
                                    last_name=family,
                                    defaults={
                                        'affiliation': author_data.get('affiliation', [{}])[0].get('name', '')
                                        if author_data.get('affiliation') else ''
                                    }
                                )
                                pub.authors.add(person)
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"Error adding author {given} {family}: {str(e)}"))
                        
                        pub.save()
                        self.stdout.write(self.style.SUCCESS(f"  Added publication: {title}"))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing Crossref item: {str(e)}"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching from Crossref: {str(e)}"))