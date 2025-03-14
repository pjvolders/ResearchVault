import requests
import logging
import csv
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Publication, Person, AuthorOrder
from django.db import transaction
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Add publications to the database by DOI or from a CSV file containing DOIs'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--doi',
            type=str,
            help='The DOI of a single publication to add'
        )
        group.add_argument(
            '--csv',
            type=str,
            help='Path to a CSV file containing DOIs in a column named "doi"'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )

    def handle(self, *args, **options):
        doi = options.get('doi')
        csv_path = options.get('csv')
        dry_run = options.get('dry_run')
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made to the database"))
        
        if doi:
            self.stdout.write(self.style.NOTICE(f"Fetching publication with DOI: {doi}"))
            self.add_by_doi(doi, dry_run)
        elif csv_path:
            self.import_from_csv(csv_path, dry_run)
    
    def import_from_csv(self, csv_path, dry_run=False):
        """
        Import DOIs from a CSV file with a column named 'doi'
        """
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                if 'doi' not in reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f"CSV file must contain a column named 'doi'"))
                    return
                
                doi_count = 0
                success_count = 0
                
                for row in reader:
                    doi = row.get('doi', '').strip()
                    if doi:
                        doi_count += 1
                        self.stdout.write(self.style.NOTICE(f"Processing DOI {doi_count}: {doi}"))
                        try:
                            result = self.add_by_doi(doi, dry_run)
                            if result:
                                success_count += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Error adding DOI {doi}: {str(e)}"))
                
                self.stdout.write(self.style.SUCCESS(f"Processed {doi_count} DOIs from CSV file. Successfully imported {success_count} publications."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file {csv_path}: {str(e)}"))
    
    def add_by_doi(self, doi, dry_run=False):
        """
        Add a single publication by DOI using the Crossref API
        
        Returns:
            bool: True if the publication was successfully processed, False otherwise
        """
        try:
            # Clean up DOI
            cleaned_doi = doi.strip()
            
            # Check if publication already exists
            if Publication.objects.filter(doi=cleaned_doi).exists():
                self.stdout.write(self.style.WARNING(f"Publication with DOI {cleaned_doi} already exists"))
                return False
            
            # Fetch from Crossref API
            self.stdout.write(f"Fetching metadata from Crossref for DOI: {cleaned_doi}")
            url = f"https://api.crossref.org/works/{cleaned_doi}"
            
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            item = data.get('message', {})
            
            if not item:
                self.stdout.write(self.style.ERROR(f"No data found for DOI: {cleaned_doi}"))
                return False
                
            # Extract basic info
            title = item.get('title', [''])[0]
            if not title:
                self.stdout.write(self.style.ERROR(f"No title found for DOI: {cleaned_doi}"))
                return False
                
            if dry_run:
                self.stdout.write(f"Would import: {title}")
                self.stdout.write(f"Authors: {', '.join([author.get('given', '') + ' ' + author.get('family', '') for author in item.get('author', [])])}")
                return True
            
            # Create publication
            with transaction.atomic():
                pub = Publication()
                pub.title = title
                pub.doi = cleaned_doi
                
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
                    
                # Set abstract if available
                if 'abstract' in item:
                    pub.abstract = item['abstract']
                    
                # Set URL
                if 'URL' in item:
                    pub.url = item['URL']
                    
                # Save the publication
                pub.save()
                
                # Get affiliations map to use later
                affiliations = {}
                if 'institution' in item:
                    for inst in item.get('institution', []):
                        if 'id' in inst and 'name' in inst:
                            affiliations[inst['id']] = inst['name']
                
                # Add authors
                authors_data = item.get('author', [])
                for i, author_data in enumerate(authors_data):
                    given = author_data.get('given', '')
                    family = author_data.get('family', '')
                    
                    if not family:  # Skip if no family name
                        continue
                        
                    # Get affiliation for this author
                    affiliation = ''
                    if 'affiliation' in author_data and author_data['affiliation']:
                        if isinstance(author_data['affiliation'], list) and author_data['affiliation']:
                            # Direct name in first affiliation
                            if 'name' in author_data['affiliation'][0]:
                                affiliation = author_data['affiliation'][0]['name']
                            # Reference to institution
                            elif 'id' in author_data['affiliation'][0] and author_data['affiliation'][0]['id'] in affiliations:
                                affiliation = affiliations[author_data['affiliation'][0]['id']]
                    
                    # Try to match existing Person or create new one
                    try:
                        person, created = Person.objects.get_or_create(
                            first_name=given,
                            last_name=family,
                            defaults={'affiliation': affiliation}
                        )
                        
                        # Determine contribution type based on position
                        contribution_type = 'normal'
                        if i == 0:
                            contribution_type = 'first'
                        elif i == len(authors_data) - 1:
                            contribution_type = 'last'
                            
                        # Check for corresponding author
                        if author_data.get('sequence') == 'first' or 'corresponding-author-id' in author_data:
                            pub.corresponding_author = person
                            
                            # If this is also the first or last author, we'll mark them as corresponding in the AuthorOrder
                            if i == 0 or i == len(authors_data) - 1:
                                contribution_type = 'corresponding'
                            
                        # Create author order with position and contribution type
                        AuthorOrder.objects.create(
                            publication=pub,
                            person=person,
                            order=i,
                            contribution_type=contribution_type
                        )
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error adding author {given} {family}: {str(e)}"))
                
                pub.save()
                self.stdout.write(self.style.SUCCESS(f"Added publication: {title}"))
                return True
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error adding publication with DOI {doi}: {str(e)}"))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return False