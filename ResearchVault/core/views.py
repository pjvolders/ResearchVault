from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from .models import Publication, Person

# Create your views here.
class PublicationListView(ListView):
    model = Publication
    template_name = 'core/publication_list.html'
    context_object_name = 'publications'
    paginate_by = 10
    ordering = ['-publication_year', 'title']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by year if provided in URL
        year = self.request.GET.get('year')
        if year and year.isdigit():
            queryset = queryset.filter(publication_year=int(year))
            
        # Filter by author if provided in URL
        author_id = self.request.GET.get('author')
        if author_id and author_id.isdigit():
            queryset = queryset.filter(authors__id=int(author_id))
            
        # Filter by search term if provided
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add publication years for filtering
        years = Publication.objects.values_list('publication_year', flat=True).distinct().order_by('-publication_year')
        context['years'] = [year for year in years if year is not None]
        
        # Add authors for filtering
        context['authors'] = Person.objects.all().order_by('last_name', 'first_name')
        
        # Add current filters
        context['current_year'] = self.request.GET.get('year', '')
        context['current_author'] = self.request.GET.get('author', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        return context


class PublicationDetailView(DetailView):
    model = Publication
    template_name = 'core/publication_detail.html'
    context_object_name = 'publication'
    

def home_view(request):
    recent_publications = Publication.objects.order_by('-publication_year', '-created_at')[:5]
    total_publications = Publication.objects.count()
    total_authors = Person.objects.count()
    
    context = {
        'recent_publications': recent_publications,
        'total_publications': total_publications,
        'total_authors': total_authors,
    }
    
    return render(request, 'core/home.html', context)
