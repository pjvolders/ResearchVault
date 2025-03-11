from django.contrib import admin
from .models import Publication, Person, AuthorOrder

# Inline for AuthorOrder to manage in the Publication admin
class AuthorOrderInline(admin.TabularInline):
    model = AuthorOrder
    extra = 1
    verbose_name = "Author"
    verbose_name_plural = "Authors (in order)"

# Register your models here.
@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'affiliation', 'email', 'orcid')
    search_fields = ('last_name', 'first_name', 'email', 'orcid', 'affiliation')
    list_filter = ('affiliation',)

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_authors', 'journal', 'publication_year', 'doi', 'citation_count')
    list_filter = ('publication_year', 'research_field')
    search_fields = ('title', 'abstract', 'keywords', 'doi', 'pmid', 'arxiv_id')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [AuthorOrderInline]
    
    def get_authors(self, obj):
        return ", ".join([str(author) for author in obj.get_ordered_authors()])
    get_authors.short_description = 'Authors'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'abstract', 'corresponding_author')
        }),
        ('Publication Details', {
            'fields': ('journal', 'conference', 'volume', 'issue', 'pages', 'publication_date', 'publication_year')
        }),
        ('Identifiers', {
            'fields': ('doi', 'pmid', 'arxiv_id', 'isbn')
        }),
        ('Files and Links', {
            'fields': ('url', 'pdf_file', 'supplementary_materials')
        }),
        ('Classification', {
            'fields': ('keywords', 'research_field')
        }),
        ('Metrics', {
            'fields': ('citation_count', 'impact_factor')
        }),
        ('Personal', {
            'fields': ('notes',)
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# Register the AuthorOrder model separately
@admin.register(AuthorOrder)
class AuthorOrderAdmin(admin.ModelAdmin):
    list_display = ('publication', 'person', 'order')
    list_filter = ('publication',)
    search_fields = ('publication__title', 'person__first_name', 'person__last_name')
    ordering = ('publication', 'order')
