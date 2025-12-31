#!/bin/bash
# Camera Trap Species Detection Platform - Automated Deployment Script
#
# Copyright (c) 2025 Omar Miranda
# SPDX-License-Identifier: Apache-2.0

set -e

echo "========================================"
echo "Species Detection Platform Deployment"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

command -v aws >/dev/null 2>&1 || { echo -e "${RED}AWS CLI is required but not installed.${NC}" >&2; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo -e "${RED}Terraform is required but not installed.${NC}" >&2; exit 1; }
command -v psql >/dev/null 2>&1 || { echo -e "${RED}PostgreSQL client is required but not installed.${NC}" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Python 3 is required but not installed.${NC}" >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo -e "${RED}Node.js is required but not installed.${NC}" >&2; exit 1; }

echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Step 1: Deploy infrastructure
echo "Step 1: Deploying infrastructure with Terraform..."
cd infrastructure/terraform

if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}terraform.tfvars not found. Please copy terraform.tfvars.example and configure it.${NC}"
    exit 1
fi

terraform init
terraform plan -out=tfplan
echo ""
read -p "Do you want to apply this Terraform plan? (yes/no) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform apply tfplan
    echo -e "${GREEN}✓ Infrastructure deployed${NC}"
else
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Get outputs
DB_ENDPOINT=$(terraform output -raw rds_endpoint)
DB_SECRET_ARN=$(terraform output -raw db_secret_arn)
LAMBDA_NAME=$(terraform output -raw lambda_function_name)

echo ""
echo -e "${GREEN}Infrastructure outputs:${NC}"
echo "  RDS Endpoint: $DB_ENDPOINT"
echo "  DB Secret ARN: $DB_SECRET_ARN"
echo "  Lambda Function: $LAMBDA_NAME"
echo ""

# Step 2: Get database credentials
echo "Step 2: Retrieving database credentials..."
DB_CREDENTIALS=$(aws secretsmanager get-secret-value --secret-id "$DB_SECRET_ARN" --query SecretString --output text)
DB_HOST=$(echo "$DB_CREDENTIALS" | jq -r .host)
DB_USER=$(echo "$DB_CREDENTIALS" | jq -r .username)
DB_PASSWORD=$(echo "$DB_CREDENTIALS" | jq -r .password)
DB_NAME=$(echo "$DB_CREDENTIALS" | jq -r .dbname)

export PGPASSWORD="$DB_PASSWORD"

echo -e "${GREEN}✓ Database credentials retrieved${NC}"
echo ""

# Step 3: Deploy database schema
echo "Step 3: Deploying database schema..."
cd "$PROJECT_ROOT/database/migrations"

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f 001_initial_schema.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database schema deployed${NC}"
else
    echo -e "${RED}✗ Database schema deployment failed${NC}"
    exit 1
fi
echo ""

# Step 4: Package and deploy Lambda
echo "Step 4: Packaging and deploying Lambda function..."
cd "$PROJECT_ROOT/backend/lambda/detection_pipeline"

# Create package directory
rm -rf package
mkdir -p package

# Install dependencies
pip3 install -r requirements.txt -t package/ --quiet

# Copy Lambda code
cp handler.py megadetector.py speciesnet.py database.py package/
cp ../common/utils.py package/

# Create ZIP
cd package
zip -r ../deployment.zip . > /dev/null 2>&1
cd ..

# Upload to Lambda
aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --zip-file fileb://deployment.zip \
    > /dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Lambda function deployed${NC}"
else
    echo -e "${RED}✗ Lambda deployment failed${NC}"
    exit 1
fi

# Update environment variables
aws lambda update-function-configuration \
    --function-name "$LAMBDA_NAME" \
    --environment "Variables={DB_HOST=$DB_HOST,DB_NAME=$DB_NAME,DB_USER=$DB_USER,DB_PASSWORD_SECRET_ID=$DB_SECRET_ARN,MEGADETECTOR_THRESHOLD=0.6,SPECIESNET_THRESHOLD=0.5}" \
    > /dev/null

echo ""

# Step 5: Install dashboard dependencies
echo "Step 5: Setting up Next.js dashboard..."
cd "$PROJECT_ROOT/dashboard"

if [ ! -f ".env.local" ]; then
    echo "Creating .env.local file..."
    cat > .env.local <<EOF
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME
NEXT_PUBLIC_MAPBOX_TOKEN=
NEXT_PUBLIC_API_URL=http://localhost:3000
EOF
fi

npm install --silent

echo -e "${GREEN}✓ Dashboard dependencies installed${NC}"
echo ""

# Completion
echo "========================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Download ML models to backend/layers/ml-models/"
echo "  2. Deploy Lambda layer with: ./deploy-layer.sh"
echo "  3. Configure S3 event trigger"
echo "  4. Start dashboard: cd dashboard && npm run dev"
echo ""
echo "Access the dashboard at: http://localhost:3000"
echo ""
