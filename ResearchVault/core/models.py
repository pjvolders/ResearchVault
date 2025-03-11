from django.db import models
from django.utils import timezone

# Create your models here.
class Person(models.Model):
    first_name = models.CharField(max_length=100, help_text="First name of the person")
    last_name = models.CharField(max_length=100, help_text="Last name of the person")
    email = models.EmailField(blank=True, help_text="Email address")
    orcid = models.CharField(max_length=19, blank=True, help_text="ORCID identifier")
    affiliation = models.CharField(max_length=255, blank=True, help_text="Primary institutional affiliation")
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    class Meta:
        verbose_name_plural = "People"
        ordering = ['last_name', 'first_name']


class Publication(models.Model):
    # Basic publication information
    title = models.CharField(max_length=500, help_text="Title of the publication")
    abstract = models.TextField(blank=True, help_text="Abstract of the publication")
    
    # Authors and affiliation (using through model for ordering)
    authors = models.ManyToManyField(
        Person, 
        through='AuthorOrder',
        related_name='publications', 
        help_text="Authors of the publication"
    )
    corresponding_author = models.ForeignKey(
        Person, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='corresponding_publications',
        help_text="Corresponding author"
    )
    
    # Publication details
    journal = models.CharField(max_length=255, blank=True, help_text="Journal name")
    conference = models.CharField(max_length=255, blank=True, help_text="Conference name")
    volume = models.CharField(max_length=50, blank=True, help_text="Volume number")
    issue = models.CharField(max_length=50, blank=True, help_text="Issue number")
    pages = models.CharField(max_length=50, blank=True, help_text="Page range")
    publication_date = models.DateField(null=True, blank=True, help_text="Date of publication")
    publication_year = models.PositiveIntegerField(null=True, blank=True, help_text="Year of publication")
    
    # Identifiers
    doi = models.CharField(max_length=100, blank=True, help_text="Digital Object Identifier")
    pmid = models.CharField(max_length=20, blank=True, help_text="PubMed ID")
    arxiv_id = models.CharField(max_length=50, blank=True, help_text="arXiv ID")
    isbn = models.CharField(max_length=20, blank=True, help_text="ISBN for books")
    
    # URLs and file references
    url = models.URLField(blank=True, help_text="URL to the publication")
    pdf_file = models.FileField(upload_to='publications/pdfs/', blank=True, null=True, help_text="PDF file of the publication")
    supplementary_materials = models.FileField(upload_to='publications/supplementary/', blank=True, null=True, help_text="Supplementary materials")
    
    # Classification and keywords
    keywords = models.TextField(blank=True, help_text="Keywords (comma separated)")
    research_field = models.CharField(max_length=100, blank=True, help_text="Field of research")
    
    # Citation metrics
    citation_count = models.PositiveIntegerField(default=0, help_text="Number of citations")
    impact_factor = models.FloatField(null=True, blank=True, help_text="Journal impact factor")
    
    # Notes and custom fields
    notes = models.TextField(blank=True, help_text="Personal notes about the publication")
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_keywords_list(self):
        """Return keywords as a list of strings."""
        if not self.keywords:
            return []
        return [kw.strip() for kw in self.keywords.split(',') if kw.strip()]
    
    def get_ordered_authors(self):
        """Return authors in the correct order."""
        return [ao.person for ao in self.authororder_set.order_by('order')]
    
    class Meta:
        ordering = ['-publication_year', 'title']


class AuthorOrder(models.Model):
    """Through model to maintain author order in publications."""
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, help_text="Order of the author in the publication")
    
    class Meta:
        ordering = ['publication', 'order']
        unique_together = ('publication', 'person')
        verbose_name = "Author Order"
        verbose_name_plural = "Author Orders"
