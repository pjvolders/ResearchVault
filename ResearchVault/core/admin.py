from django.contrib import admin
from django.db import models, transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import path
from django.http import HttpResponseRedirect

from .models import Publication, Person, AuthorOrder, Dissertation

# Inline for AuthorOrder to manage in the Publication admin
class AuthorOrderInline(admin.TabularInline):
    model = AuthorOrder
    extra = 1
    verbose_name = "Author"
    verbose_name_plural = "Authors (in order)"
    fields = ('person', 'order', 'contribution_type')

def merge_people(modeladmin, request, queryset):
    """
    Admin action to merge multiple Person objects into one.
    Handles:
    - AuthorOrder relationships
    - corresponding_author relationships in Publication
    """
    if 'apply' in request.POST:
        try:
            with transaction.atomic():
                primary_id = int(request.POST.get('primary_record'))
                primary_person = Person.objects.get(id=primary_id)
                persons_to_merge = queryset.exclude(id=primary_id)
                
                # Update corresponding_author relationships
                for person in persons_to_merge:
                    Publication.objects.filter(corresponding_author=person).update(
                        corresponding_author=primary_person
                    )
                
                # Handle AuthorOrder relationships
                for person in persons_to_merge:
                    # For each publication where the person is an author
                    for author_order in AuthorOrder.objects.filter(person=person):
                        # Check if primary person already has an entry for this publication
                        existing_order = AuthorOrder.objects.filter(
                            person=primary_person,
                            publication=author_order.publication
                        ).first()
                        
                        if existing_order:
                            # Primary person is already an author, keep the earlier order position
                            if existing_order.order > author_order.order:
                                # Shift other authors down
                                AuthorOrder.objects.filter(
                                    publication=author_order.publication,
                                    order__gte=author_order.order,
                                    order__lt=existing_order.order
                                ).update(order=models.F('order') + 1)
                                
                                # Update primary person's order
                                existing_order.order = author_order.order
                                existing_order.save()
                            
                            # Delete the duplicate author entry
                            author_order.delete()
                        else:
                            # Primary person isn't an author, reassign the entry
                            author_order.person = primary_person
                            author_order.save()
                
                # Delete the merged persons
                persons_to_merge.delete()
                
                modeladmin.message_user(
                    request,
                    f"Successfully merged {persons_to_merge.count()} records into {primary_person}",
                    messages.SUCCESS
                )
                
                return HttpResponseRedirect(request.get_full_path())
        except Exception as e:
            modeladmin.message_user(
                request,
                f"Error during merge: {str(e)}",
                messages.ERROR
            )
            return HttpResponseRedirect(request.get_full_path())
    
    return render(
        request,
        'admin/core/person/merge_confirmation.html',
        context={
            'persons': queryset,
            'person_ids': [str(pk) for pk in queryset.values_list('pk', flat=True)],
            'title': 'Merge selected people records',
        }
    )

merge_people.short_description = "Merge selected people records"

# Register your models here.
@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'affiliation', 'email', 'orcid')
    search_fields = ('last_name', 'first_name', 'email', 'orcid', 'affiliation')
    list_filter = ('affiliation',)
    actions = [merge_people]

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
    list_display = ('publication', 'person', 'order', 'contribution_type')
    list_filter = ('publication', 'contribution_type')
    search_fields = ('publication__title', 'person__first_name', 'person__last_name')
    ordering = ('publication', 'order')

# Register the Dissertation model
class CoPromoterInline(admin.TabularInline):
    model = Dissertation.copromoters.through
    extra = 1
    verbose_name = "Co-promoter"
    verbose_name_plural = "Co-promoters"

@admin.register(Dissertation)
class DissertationAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'promoter', 'degree', 'defense_date', 'institution')
    list_filter = ('degree', 'defense_date', 'institution', 'department')
    search_fields = ('title', 'abstract', 'keywords', 'author__first_name', 'author__last_name', 
                    'promoter__first_name', 'promoter__last_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CoPromoterInline]
    exclude = ('copromoters',)  # Exclude this field as we're using the inline instead
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'author', 'promoter', 'supervisor', 'degree')
        }),
        ('Dates', {
            'fields': ('start_date', 'defense_date')
        }),
        ('Institution', {
            'fields': ('institution', 'department')
        }),
        ('Content', {
            'fields': ('abstract', 'keywords')
        }),
        ('Files and Links', {
            'fields': ('url', 'pdf_file')
        }),
        ('Personal', {
            'fields': ('notes',)
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
