# Camera Trap Species Detection Platform

[![AWS](https://img.shields.io/badge/AWS-Cloud-orange)](https://aws.amazon.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.1.1-black)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

An AI-powered platform for automated analysis of camera trap images, helping ecologists save time and focus on conservation efforts through automated species detection and classification.

## Overview

This platform streamlines the workflow of ecologists dealing with camera trap images by:

- **Automated Animal Detection** using MegaDetector v5.0
- **Species Classification** using SpeciesNet (5,000+ species)
- **Geospatial Visualization** with interactive maps
- **Real-time Dashboard** for monitoring and analysis
- **PostgreSQL Database** for efficient data management
- **Built on AWS** infrastructure for scalability

## Key Features

- **AI-Powered Detection**: Automatically detect and classify animals in camera trap images
- **Species List Dashboard**: Browse all detected species with filtering and search
- **Interactive Map**: Visualize species distribution across camera locations
- **Confidence Scoring**: Review low-confidence detections for accuracy
- **EXIF Data Extraction**: Capture GPS, timestamp, and camera metadata
- **Export Capabilities**: Download data in CSV/JSON formats
- **Integration Ready**: Works with existing AWS sensor data pipeline

## Architecture

```
Camera Images → S3 → Lambda (AI Processing) → PostgreSQL → Next.js Dashboard
                           ↓
                   MegaDetector + SpeciesNet
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## Technology Stack

### Backend
- **AWS Lambda**: Serverless image processing
- **PostgreSQL RDS**: Detection and species database
- **S3**: Image storage with existing pipeline integration
- **DynamoDB**: File tracking (from sensor platform)
- **Python 3.11**: Lambda runtime

### AI Models
- **MegaDetector v5.0**: YOLOv5-based animal detection
- **SpeciesNet**: iNaturalist-trained species classifier

### Frontend
- **Next.js 16.1.1**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Styling
- **Mapbox/Leaflet**: Interactive maps
- **Shadcn/ui**: UI components

### Infrastructure
- **Terraform**: Infrastructure as Code
- **CloudWatch**: Monitoring and logging
- **Secrets Manager**: Secure credential storage

## Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.6
- Node.js >= 20
- Python 3.11+
- PostgreSQL client (optional, for local testing)

### 1. Deploy Infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

This creates:
- PostgreSQL RDS instance
- Lambda function for AI processing
- Lambda layers with ML models
- VPC and security groups
- Required IAM roles

### 2. Deploy Database Schema

```bash
# Get RDS endpoint from Terraform output
export DB_HOST=$(terraform output -raw rds_endpoint)
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id species-detection-db --query SecretString --output text | jq -r .password)

# Run migrations
cd ../../database/migrations
psql -h $DB_HOST -U species_admin -d species_detection -f 001_initial_schema.sql
```

### 3. Deploy Lambda Function

```bash
cd ../../backend/lambda/detection_pipeline
pip install -r requirements.txt -t package/
cd package && zip -r ../deployment.zip . && cd ..
zip -g deployment.zip handler.py

aws lambda update-function-code \
  --function-name species-detection-pipeline \
  --zip-file fileb://deployment.zip
```

### 4. Set Up Dashboard

```bash
cd ../../../dashboard
npm install

# Create .env.local file
cat > .env.local << EOF
DATABASE_URL=postgresql://species_admin:${DB_PASSWORD}@${DB_HOST}/species_detection
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here
EOF

# Run development server
npm run dev
```

Visit `http://localhost:3000` to see the dashboard.

### 5. Test with Sample Images

```bash
cd ../scripts
python test-upload.py --bucket your-bucket-name --type jpeg --count 10
```

## Project Structure

```
speciesDetection/
├── README.md                          # This file
├── ARCHITECTURE.md                    # System architecture
├── infrastructure/
│   └── terraform/                     # AWS infrastructure
│       ├── main.tf
│       ├── rds.tf                     # PostgreSQL database
│       ├── lambda.tf                  # Lambda functions
│       ├── vpc.tf                     # Network configuration
│       ├── variables.tf
│       └── outputs.tf
├── backend/
│   ├── lambda/
│   │   ├── detection_pipeline/        # Main Lambda function
│   │   │   ├── handler.py             # Lambda entry point
│   │   │   ├── megadetector.py        # MegaDetector integration
│   │   │   ├── speciesnet.py          # SpeciesNet integration
│   │   │   ├── database.py            # PostgreSQL operations
│   │   │   └── requirements.txt
│   │   └── common/                    # Shared utilities
│   │       └── utils.py
│   └── layers/
│       └── ml-models/                 # Lambda layer for models
│           └── download-models.sh
├── database/
│   └── migrations/
│       ├── 001_initial_schema.sql     # Database schema
│       └── 002_seed_species.sql       # Species catalog
├── dashboard/                         # Next.js application
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Overview dashboard
│   │   ├── species/
│   │   │   └── page.tsx               # Species list
│   │   ├── map/
│   │   │   └── page.tsx               # Interactive map
│   │   └── api/                       # API routes
│   │       ├── species/
│   │       └── detections/
│   ├── components/                    # React components
│   ├── lib/                          # Utilities
│   ├── package.json
│   └── next.config.js
├── scripts/
│   ├── deploy.sh                      # Deployment automation
│   ├── test-upload.py                 # Upload test images
│   └── seed-species.py                # Populate species catalog
└── docs/
    ├── deployment-guide.md
    ├── user-guide.md
    └── api-reference.md
```

## Database Schema

### Core Tables

- **species**: Species catalog with taxonomy and conservation status
- **images**: Image metadata including EXIF and GPS data
- **locations**: Camera trap locations and habitat information
- **detections**: Detection results with bounding boxes and confidence scores

See [database/migrations/001_initial_schema.sql](database/migrations/001_initial_schema.sql) for full schema.

## Dashboard Features

### Species List (`/species`)
- View all detected species
- Filter by taxonomy, conservation status, date range
- Search by scientific or common name
- Sort by observation frequency
- Export to CSV

### Map View (`/map`)
- Interactive map of camera locations
- Color-coded markers by species diversity
- Click markers to view species at location
- Heatmap overlay for detection density
- Filter by species and date range

### Dashboard (`/dashboard`)
- Total images processed
- Unique species detected
- Recent detections timeline
- Top detected species
- Detection confidence metrics

### Image Gallery
- Browse all processed images
- View bounding boxes overlaid on images
- Filter by species, date, confidence
- Review and verify detections

## ML Models

### MegaDetector v5.0
- **Purpose**: Detect animals, people, vehicles in camera trap images
- **Architecture**: YOLOv5
- **Accuracy**: ~95% on camera trap images
- **Output**: Bounding boxes with confidence scores

### SpeciesNet
- **Purpose**: Classify detected animals by species
- **Training**: iNaturalist dataset
- **Species**: 5,000+ wildlife species
- **Accuracy**: 80-90% top-5 accuracy (varies by species)

## Cost Estimates

### Monthly Costs (10,000 images/month)

| Service | Cost | Notes |
|---------|------|-------|
| RDS PostgreSQL (db.t3.micro) | $15 | 20GB storage |
| Lambda Executions | $25 | ~30s per image |
| Lambda Layers | $5 | Model storage |
| S3 Storage | $10 | Image storage |
| Data Transfer | $5 | Outbound |
| **Total** | **~$60/month** | Scales with volume |

## Performance

- **Processing Time**: 20-40 seconds per image
- **Concurrent Processing**: Up to 100 images simultaneously
- **Database Query**: <100ms for most queries
- **Dashboard Load**: <2 seconds initial page load

## Integration with Sensor Platform

This platform integrates with the [global-sensor-data-management](https://github.com/omiranda/global-sensor-data-management) platform:

- Uses existing S3 buckets and hierarchical structure
- Leverages DynamoDB tracking table
- Extends Lambda processing pipeline
- Shares CloudWatch monitoring
- Compatible with existing upload workflows

## Development

### Run Locally

```bash
# Start dashboard
cd dashboard
npm run dev

# Run Lambda locally (with SAM or LocalStack)
cd backend/lambda/detection_pipeline
sam local invoke -e test-event.json
```

### Testing

```bash
# Frontend tests
cd dashboard
npm test

# Backend tests
cd backend/lambda/detection_pipeline
pytest tests/
```

## Deployment

See [docs/deployment-guide.md](docs/deployment-guide.md) for detailed deployment instructions.

### Production Checklist

- [ ] Configure production database credentials
- [ ] Set up RDS automated backups
- [ ] Configure Lambda reserved concurrency
- [ ] Set up CloudWatch alarms
- [ ] Configure VPC security groups
- [ ] Set up SSL/TLS for dashboard
- [ ] Configure authentication (Cognito/Auth0)
- [ ] Set up monitoring dashboards
- [ ] Configure log retention policies
- [ ] Set up automated testing

## Contributing

Contributions welcome! Please read the contributing guidelines.

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Support

For questions or issues:
- Create an issue in GitHub
- Email: support@example.com
- Documentation: [docs/](docs/)

## Acknowledgments

- MegaDetector by Microsoft AI for Earth
- iNaturalist for species classification models
- Camera trap ecologist community for requirements and feedback

---

**Built with ❤️ for conservation ecologists worldwide**
