# Image Optimization for Web Delivery

This document explains the automated image compression and optimization system for the Camera Trap Species Detection Platform.

## Overview

Camera trap images are typically large (5-20MB) high-resolution files optimized for analysis, not web delivery. The platform automatically generates three optimized versions of each image for efficient dashboard loading:

| Size | Max Dimension | Quality | Format | Use Case |
|------|---------------|---------|--------|----------|
| **Thumbnail** | 200px | 80% | JPEG | Lists, grids, previews |
| **Preview** | 800px | 85% | JPEG | Modal view, detailed inspection |
| **Full** | 1920px | 90% | JPEG | Full-resolution viewing |

## How It Works

### 1. Automatic Processing

When an image is uploaded to S3 and processed by the Lambda function:

1. Original image is downloaded from S3
2. Three optimized versions are generated
3. Optimized images are uploaded to S3 in `/optimized/` subdirectory
4. URLs are stored in the database
5. Dashboard uses optimized URLs for display

### 2. Processing Pipeline

```
Original Image (5MB)
    ↓
ImageOptimizer
    ├─→ Thumbnail (20KB)  → s3://bucket/path/optimized/image_thumbnail.jpg
    ├─→ Preview (150KB)   → s3://bucket/path/optimized/image_preview.jpg
    └─→ Full (800KB)      → s3://bucket/path/optimized/image_full.jpg
    ↓
Database (URLs stored)
```

### 3. Optimization Techniques

- **Resizing**: Maintains aspect ratio, only downscales (never upscales)
- **Format Conversion**: Converts RGBA/PNG to RGB JPEG for smaller size
- **Quality Adjustment**: Different quality levels for different use cases
- **Progressive JPEG**: Better perceived loading on slow connections
- **Optimize Flag**: PIL optimization for minimal file size

## Implementation

### Backend (Lambda)

The `ImageOptimizer` class in [`backend/lambda/common/image_optimizer.py`](../backend/lambda/common/image_optimizer.py) handles all optimization:

```python
from image_optimizer import ImageOptimizer

optimizer = ImageOptimizer(s3_client=boto3.client('s3'))

# Generate all sizes
optimized_urls = optimizer.process_image_for_web(
    bucket='my-bucket',
    key='project/country/client/sensor/2024-01-01/image.jpg',
    make_public=False  # Use pre-signed URLs
)

# Result:
# {
#     'thumbnail': 'https://s3.amazonaws.com/...',
#     'preview': 'https://s3.amazonaws.com/...',
#     'full': 'https://s3.amazonaws.com/...'
# }
```

### Database Schema

The `images` table includes URL columns:

```sql
ALTER TABLE images
ADD COLUMN thumbnail_url VARCHAR(1000),
ADD COLUMN preview_url VARCHAR(1000),
ADD COLUMN full_url VARCHAR(1000);
```

See migration: [`database/migrations/002_add_optimized_image_urls.sql`](../database/migrations/002_add_optimized_image_urls.sql)

### Frontend (Dashboard)

The dashboard uses optimized URLs from the database:

```typescript
// Use thumbnail for grid view
<img src={image.thumbnail_url} alt="Thumbnail" />

// Use preview for modal/detail view
<img src={image.preview_url} alt="Preview" />

// Use full for full-screen view
<img src={image.full_url} alt="Full size" />
```

## S3 Structure

```
my-bucket/
├── project/country/client/sensor/2024-01-01/
│   ├── image001.jpg          # Original (5MB)
│   └── optimized/
│       ├── image001_thumbnail.jpg  # 20KB
│       ├── image001_preview.jpg    # 150KB
│       └── image001_full.jpg       # 800KB
```

## Performance Benefits

### Before Optimization
- Loading 100 images in grid: **500MB** (5MB × 100)
- Initial page load: **10-30 seconds** on average connection
- Mobile data usage: **Excessive**

### After Optimization
- Loading 100 thumbnails: **2MB** (20KB × 100)
- Initial page load: **<2 seconds**
- Mobile data usage: **95% reduction**

## Configuration

Environment variables for Lambda (optional):

```bash
# Enable/disable optimization (default: enabled)
IMAGE_OPTIMIZATION_ENABLED=true

# Custom quality settings
THUMBNAIL_QUALITY=80
PREVIEW_QUALITY=85
FULL_QUALITY=90

# Custom size limits
THUMBNAIL_MAX_DIMENSION=200
PREVIEW_MAX_DIMENSION=800
FULL_MAX_DIMENSION=1920
```

## S3 Permissions

The Lambda function needs these S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket/*"
    }
  ]
}
```

## Cost Optimization

### Storage Costs
- **Original**: 5MB → $0.00012/month (S3 Standard)
- **Optimized (3 files)**: 1MB → $0.00002/month
- **Total per image**: $0.00014/month

For 100,000 images:
- **Original only**: $12/month
- **With optimized**: $14/month
- **Extra cost**: $2/month
- **Data transfer savings**: $100+/month

### Caching
Optimized images include cache headers:
```
Cache-Control: max-age=31536000  # 1 year
```

This reduces S3 GET requests and improves performance.

## URL Security

By default, optimized images use **pre-signed URLs** valid for 7 days:

```python
# Generate pre-signed URL (default)
urls = optimizer.process_image_for_web(
    bucket='my-bucket',
    key='path/to/image.jpg',
    make_public=False  # Pre-signed URLs
)

# Make images publicly accessible (optional)
urls = optimizer.process_image_for_web(
    bucket='my-bucket',
    key='path/to/image.jpg',
    make_public=True  # Public URLs
)
```

### Pre-signed URLs (Recommended)
- ✅ Secure - limited time access
- ✅ No bucket policy changes needed
- ⚠️ URLs expire (regenerate periodically)

### Public URLs
- ✅ Permanent - never expire
- ✅ Cacheable by CDN
- ⚠️ Requires bucket ACL or policy

## Error Handling

Image optimization is **non-critical** - if it fails, processing continues:

```python
try:
    optimized_urls = optimizer.process_image_for_web(bucket, key)
    db_manager.update_image_urls(image_id, optimized_urls)
except Exception as e:
    logger.warning(f"Image optimization failed (non-critical): {e}")
    # Continue processing - original image still available
```

## Monitoring

CloudWatch metrics to monitor:

- `ImageOptimization.Success` - Successful optimizations
- `ImageOptimization.Failure` - Failed optimizations
- `ImageOptimization.Duration` - Processing time
- `ImageOptimization.CompressionRatio` - Average compression achieved

## Manual Optimization

To manually optimize existing images:

```bash
# Python script
python scripts/optimize_images.py --bucket my-bucket --prefix project/

# AWS CLI + Lambda invoke
aws lambda invoke \
  --function-name species-detection-pipeline \
  --payload '{"bucket": "my-bucket", "key": "path/image.jpg", "operation": "optimize"}' \
  response.json
```

## Troubleshooting

### Images Not Optimizing

1. Check Lambda logs:
```bash
aws logs tail /aws/lambda/species-detection-pipeline --follow
```

2. Verify S3 permissions
3. Check Lambda timeout (increase if needed)
4. Verify Pillow is in Lambda layer

### Poor Compression

- Adjust quality settings
- Check original image format (some formats compress better)
- Verify resize dimensions are appropriate

### URL Expiration

Pre-signed URLs expire after 7 days. To regenerate:

```sql
-- Update all images with new pre-signed URLs
UPDATE images SET
  thumbnail_url = NULL,
  preview_url = NULL,
  full_url = NULL
WHERE processing_status = 'completed';
```

Then reprocess or use a script to regenerate URLs.

## Future Enhancements

- [ ] WebP format support (better compression)
- [ ] AVIF format support (next-gen format)
- [ ] Lazy loading with blur placeholder
- [ ] CloudFront CDN integration
- [ ] Automatic URL refresh before expiration
- [ ] Client-side caching strategy
- [ ] Responsive image srcset generation

## References

- [Pillow Documentation](https://pillow.readthedocs.io/)
- [JPEG Optimization Best Practices](https://developers.google.com/speed/docs/insights/OptimizeImages)
- [S3 Pre-signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)
