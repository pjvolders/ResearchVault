# ResearchVault Development Reference

## Commands
- **Run server**: `cd ResearchVault && python manage.py runserver`
- **Run migrations**: `cd ResearchVault && python manage.py migrate`
- **Create migrations**: `cd ResearchVault && python manage.py makemigrations [app]`
- **Run tests**: `cd ResearchVault && python manage.py test [app.TestCase]`
- **Fetch publications**: `cd ResearchVault && python manage.py fetch_publications --source=orcid --orcid=ORCID_ID`
- **Django shell**: `cd ResearchVault && python manage.py shell`

## Code Style Guidelines
- **Imports**: Group imports: stdlib, third-party, local apps; alphabetize within groups
- **Models**: Use descriptive field names with help_text; define __str__ and Meta classes
- **Views**: Use Django class-based views when possible; document view parameters
- **Templates**: Use base templates with blocks; avoid logic in templates
- **Comments**: DocStrings for classes/functions; inline comments for complex logic
- **Error handling**: Use try/except with specific exceptions; log errors with proper context
- **Naming**: snake_case for variables/functions, CamelCase for classes
- **Types**: Include docstrings with type hints for complex functions

## Project Architecture
This Django app manages scientific publications with Person, Publication, and AuthorOrder models.
The primary feature is importing publications from ORCID and maintaining author ordering.