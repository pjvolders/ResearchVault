# ResearchVault

A Django application for managing scientific publications with ORCID integration.

## Local Development

1. **Run the server**:
   ```
   cd ResearchVault && python manage.py runserver
   ```

2. **Run migrations**:
   ```
   cd ResearchVault && python manage.py migrate
   ```

3. **Create migrations**:
   ```
   cd ResearchVault && python manage.py makemigrations [app]
   ```

4. **Run tests**:
   ```
   cd ResearchVault && python manage.py test [app.TestCase]
   ```

5. **Fetch publications**:
   ```
   cd ResearchVault && python manage.py fetch_publications --source=orcid --orcid=ORCID_ID
   ```

## Google Cloud Deployment

### Prerequisites

1. Install Google Cloud SDK:
   ```
   https://cloud.google.com/sdk/docs/install
   ```

2. Initialize gcloud:
   ```
   gcloud init
   ```

3. Create a Google Cloud project:
   ```
   gcloud projects create PROJECT_ID
   ```

4. Set the project:
   ```
   gcloud config set project PROJECT_ID
   ```

### Setup Database (Cloud SQL)

1. Create a PostgreSQL instance:
   ```
   gcloud sql instances create researchvault-db \
     --database-version=POSTGRES_13 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

2. Create a database:
   ```
   gcloud sql databases create researchvault \
     --instance=researchvault-db
   ```

3. Create a user:
   ```
   gcloud sql users create researchvault-user \
     --instance=researchvault-db \
     --password=YOUR_PASSWORD
   ```

### Store Secrets

1. Enable the Secret Manager API:
   ```
   gcloud services enable secretmanager.googleapis.com
   ```

2. Create a secret for Django's SECRET_KEY:
   ```
   echo -n "your-very-secure-and-secret-key" | \
   gcloud secrets create django_secret_key --data-file=-
   ```

3. Create a secret for DATABASE_URL:
   ```
   echo -n "postgres://researchvault-user:YOUR_PASSWORD@//cloudsql/PROJECT_ID:us-central1:researchvault-db/researchvault" | \
   gcloud secrets create database_url --data-file=-
   ```

### Create Storage Bucket for Media Files

1. Create a bucket:
   ```
   gsutil mb -l us-central1 gs://PROJECT_ID-media
   ```

2. Make the bucket public:
   ```
   gsutil iam ch allUsers:objectViewer gs://PROJECT_ID-media
   ```

### Deploy to Cloud Run

1. Build and deploy with Cloud Build:
   ```
   gcloud builds submit --config cloudbuild.yaml
   ```

2. Run migrations:
   ```
   gcloud builds submit --config cloudmigrate.yaml
   ```

### Alternative: Deploy to App Engine

1. Deploy the app:
   ```
   gcloud app deploy
   ```

2. Run migrations:
   ```
   gcloud app deploy --no-promote --version=migrate app.yaml
   ```

### Access your deployed app

```
gcloud run services describe researchvault --format="value(status.url)"
```

## Monitoring and Maintenance

1. View logs:
   ```
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=researchvault"
   ```

2. Scale your service:
   ```
   gcloud run services update researchvault --min-instances=1 --max-instances=10
   ```