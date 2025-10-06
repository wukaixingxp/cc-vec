# Athena Setup Guide for Common Crawl

## Problem: `Schema 'ccindex' does not exist`

If you see this error:
```
SCHEMA_NOT_FOUND: line 13:14: Schema 'ccindex' does not exist
```

This means you need to set up the Common Crawl database and table in AWS Athena.

## Quick Fix

### Option 1: Automated Setup (Recommended)

Run the setup script:

```bash
# Make sure ATHENA_OUTPUT_BUCKET is set
export ATHENA_OUTPUT_BUCKET="s3://your-bucket/athena-results/"

# Run the automated setup
python setup_athena.py
```

### Option 2: Manual Setup via AWS Console

1. **Open AWS Athena Console**: https://console.aws.amazon.com/athena/
2. **Set Query Result Location**:
   - Go to Settings → Manage
   - Set "Query result location" to your S3 bucket (same as `ATHENA_OUTPUT_BUCKET`)
3. **Create Database**:
   ```sql
   CREATE DATABASE IF NOT EXISTS ccindex
   COMMENT 'Common Crawl index database for cc-vec queries';
   ```
4. **Create Table**:
   ```sql
   CREATE EXTERNAL TABLE IF NOT EXISTS ccindex.ccindex (
       url string,
       url_host_name string,
       fetch_time timestamp,
       fetch_status smallint,
       content_mime_type string,
       content_charset string,
       content_languages string,
       warc_filename string,
       warc_record_offset bigint,
       warc_record_length int,
       crawl string,
       subset string
   )
   STORED AS PARQUET
   LOCATION 's3://commoncrawl/cc-index/table/cc-main/warc/';
   ```

### Option 3: Use SQL File

Execute the provided SQL setup:

```bash
# Run the SQL file in Athena console or via AWS CLI
aws athena start-query-execution \
  --query-string file://setup_common_crawl_athena.sql \
  --result-configuration OutputLocation=$ATHENA_OUTPUT_BUCKET
```

## Prerequisites

### 1. Environment Variables

Set these required environment variables:

```bash
# Required: S3 bucket for Athena query results
export ATHENA_OUTPUT_BUCKET="s3://your-bucket/athena-results/"

# Required: AWS credentials
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# Optional: AWS region (defaults to us-west-2)
export AWS_DEFAULT_REGION="us-west-2"
```

### 2. AWS IAM Permissions

Your AWS credentials need these permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "athena:*",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "glue:GetDatabase",
                "glue:GetTable",
                "glue:GetPartitions"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. S3 Bucket Setup

Create an S3 bucket for Athena query results:

```bash
# Create bucket (replace with your bucket name)
aws s3 mb s3://your-bucket

# Create athena-results folder
aws s3api put-object --bucket your-bucket --key athena-results/
```

## Testing the Setup

Once setup is complete, test with:

```bash
# Test basic search
uv run cc-vec search "%.github.io" --limit 5

# Test with different crawl
uv run cc-vec search "%.github.io" --crawl "CC-MAIN-2024-30" --limit 3

# Get statistics
uv run cc-vec stats "%.github.io"
```

## Common Issues and Solutions

### Issue: Access Denied to S3 Bucket

```
❌ Access denied to bucket 'your-bucket'
```

**Solution**: Check IAM permissions and bucket policy. Ensure your AWS credentials can read/write to the bucket.

### Issue: Wrong Crawl ID

```
Query completed successfully
Found 0 results
```

**Solution**: Try different crawl IDs. Common Crawl releases data monthly:

```bash
# Try recent crawls
uv run cc-vec search "%.github.io" --crawl "CC-MAIN-2024-30" --limit 5
uv run cc-vec search "%.github.io" --crawl "CC-MAIN-2024-26" --limit 5
uv run cc-vec search "%.github.io" --crawl "CC-MAIN-2024-22" --limit 5
```

### Issue: Table Creation Fails

```
❌ Creating ccindex table failed: INVALID_PROPERTY_VALUE
```

**Solution**: The table schema might need updates. Try creating a simpler table first:

```sql
CREATE EXTERNAL TABLE ccindex.ccindex_simple (
    url string,
    fetch_status smallint,
    content_mime_type string,
    warc_filename string,
    warc_record_offset bigint,
    warc_record_length int,
    crawl string
)
STORED AS PARQUET
LOCATION 's3://commoncrawl/cc-index/table/cc-main/warc/';
```

### Issue: Region Mismatch

```
❌ The bucket is in this region: us-east-1. Please use this region to retry the request
```

**Solution**: Set the correct AWS region:

```bash
export AWS_DEFAULT_REGION="us-east-1"
```

## Available Common Crawl Datasets

Common Crawl releases data monthly. Recent crawl IDs include:

- `CC-MAIN-2024-33` (August 2024)
- `CC-MAIN-2024-30` (July 2024)
- `CC-MAIN-2024-26` (June 2024)
- `CC-MAIN-2024-22` (May 2024)
- `CC-MAIN-2024-18` (April 2024)

You can find the full list at: https://commoncrawl.org/

## Verification

After setup, verify everything works:

```bash
# Check database exists
aws athena start-query-execution \
  --query-string "SHOW DATABASES" \
  --result-configuration OutputLocation=$ATHENA_OUTPUT_BUCKET

# Check table exists
aws athena start-query-execution \
  --query-string "SHOW TABLES IN ccindex" \
  --result-configuration OutputLocation=$ATHENA_OUTPUT_BUCKET

# Test query
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM ccindex.ccindex WHERE crawl = 'CC-MAIN-2024-33' LIMIT 1" \
  --result-configuration OutputLocation=$ATHENA_OUTPUT_BUCKET
```

## Getting Help

If you continue to have issues:

1. Check AWS CloudTrail logs for detailed error messages
2. Verify your AWS region matches your S3 bucket region
3. Ensure your IAM user/role has sufficient permissions
4. Try with a different crawl ID
5. Check Common Crawl documentation: https://commoncrawl.org/

For cc-vec specific issues, check the project's issue tracker or documentation.
