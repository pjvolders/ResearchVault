from django.db import models
from django.utils import timezone

# Create your models here.
class Degree(models.TextChoices):
    PHD = 'PhD', 'PhD'
    MASTER = 'Master', 'Master'
    BACHELOR = 'Bachelor', 'Bachelor'
    OTHER = 'Other', 'Other'
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
        
    def get_authors_with_contributions(self):
        """Return authors with their contribution types."""
        return self.authororder_set.order_by('order').select_related('person')
        
    def has_first_authors(self):
        """Check if this publication has any first or co-first authors."""
        return self.authororder_set.filter(contribution_type__in=['first', 'co-first']).exists()
        
    def has_last_authors(self):
        """Check if this publication has any last or co-last authors."""
        return self.authororder_set.filter(contribution_type__in=['last', 'co-last']).exists()
        
    def has_corresponding_authors(self):
        """Check if this publication has any corresponding authors."""
        return self.authororder_set.filter(contribution_type='corresponding').exists()
    
    class Meta:
        ordering = ['-publication_year', 'title']


class AuthorOrder(models.Model):
    """Through model to maintain author order in publications."""
    CONTRIBUTION_CHOICES = [
        ('normal', 'Normal'),
        ('first', 'First Author'),
        ('co-first', 'Co-First Author'),
        ('last', 'Last Author'),
        ('co-last', 'Co-Last Author'),
        ('corresponding', 'Corresponding Author'),
    ]
    
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, help_text="Order of the author in the publication")
    contribution_type = models.CharField(
        max_length=20, 
        choices=CONTRIBUTION_CHOICES,
        default='normal',
        help_text="Type of author contribution"
    )
    
    class Meta:
        ordering = ['publication', 'order']
        unique_together = ('publication', 'person')
        verbose_name = "Author Order"
        verbose_name_plural = "Author Orders"


class Dissertation(models.Model):
    """Model representing a dissertation (PhD, Master, etc.)."""
    title = models.CharField(max_length=500, help_text="Title of the dissertation")
    author = models.ForeignKey(
        Person, 
        on_delete=models.CASCADE,
        related_name='authored_dissertations',
        help_text="Author of the dissertation"
    )
    promoter = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='promoted_dissertations',
        help_text="Main promoter/advisor of the dissertation"
    )
    copromoters = models.ManyToManyField(
        Person,
        related_name='copromoted_dissertations',
        blank=True,
        help_text="Co-promoters/co-advisors of the dissertation"
    )
    supervisor = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        related_name='supervised_dissertations',
        blank=True,
        null=True,
        help_text="Additional supervisor if different from promoter"
    )
    degree = models.CharField(
        max_length=20,
        choices=Degree.choices,
        default=Degree.PHD,
        help_text="Type of degree"
    )
    start_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when the dissertation work started"
    )
    defense_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date of the dissertation defense"
    )
    abstract = models.TextField(blank=True, help_text="Abstract of the dissertation")
    institution = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Institution where the dissertation was completed"
    )
    department = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Department or faculty within the institution"
    )
    url = models.URLField(blank=True, help_text="URL to the dissertation")
    pdf_file = models.FileField(
        upload_to='dissertations/pdfs/', 
        blank=True, 
        null=True, 
        help_text="PDF file of the dissertation"
    )
    keywords = models.TextField(blank=True, help_text="Keywords (comma separated)")
    notes = models.TextField(blank=True, help_text="Notes about the dissertation")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} ({self.get_degree_display()} by {self.author})"
    
    def get_keywords_list(self):
        """Return keywords as a list of strings."""
        if not self.keywords:
            return []
        return [kw.strip() for kw in self.keywords.split(',') if kw.strip()]
    
    class Meta:
        ordering = ['-defense_date', 'title']
        verbose_name = "Dissertation"
        verbose_name_plural = "Dissertations"
