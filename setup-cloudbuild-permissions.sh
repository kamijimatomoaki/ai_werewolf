#!/bin/bash

# Cloud Build permissions setup script
# Run this script to give Cloud Build permission to deploy to Cloud Run

echo "Setting up Cloud Build permissions for Cloud Run deployment..."

# Get the project ID
PROJECT_ID=$(gcloud config get-value project)
echo "Project ID: $PROJECT_ID"

# Get the Cloud Build service account
CLOUDBUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"
echo "Cloud Build Service Account: $CLOUDBUILD_SA"

# Grant Cloud Run Admin role to Cloud Build service account
echo "Granting Cloud Run Admin role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/run.admin"

# Grant Service Account User role (required for Cloud Run deployment)
echo "Granting Service Account User role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/iam.serviceAccountUser"

# Grant Container Registry Admin role (if not already granted)
echo "Granting Container Registry Admin role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUDBUILD_SA" \
    --role="roles/storage.admin"

echo "Permissions setup complete!"
echo ""
echo "You can now run Cloud Build to deploy to Cloud Run:"
echo "gcloud builds submit --config=cloudbuild.yaml ."