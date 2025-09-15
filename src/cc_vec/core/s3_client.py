"""S3 client for fetching Common Crawl data files."""

import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class CCS3Client:
    """Client for fetching Common Crawl data from S3."""

    def __init__(self, region_name: str = "us-east-1"):
        """Initialize S3 client for Common Crawl data.

        Args:
            region_name: AWS region, Common Crawl data is in us-east-1
        """
        self.bucket_name = "commoncrawl"
        try:
            self.s3_client = boto3.client("s3", region_name=region_name)
        except NoCredentialsError:
            logger.warning("No AWS credentials found, will attempt unsigned requests")
            self.s3_client = boto3.client(
                "s3",
                region_name=region_name,
                config=boto3.session.Config(signature_version="UNSIGNED"),
            )

    def fetch_warc_content(
        self, filename: str, offset: int, length: int
    ) -> Optional[bytes]:
        """Fetch WARC content from S3 using byte range.

        Args:
            filename: Common Crawl filename (e.g., "crawl-data/CC-MAIN-2024-33/segments/...")
            offset: Byte offset in file
            length: Number of bytes to read

        Returns:
            Raw bytes content or None if error
        """
        try:
            # Construct byte range header
            range_header = f"bytes={offset}-{offset + length - 1}"

            logger.info(
                f"Fetching {length} bytes from s3://{self.bucket_name}/{filename} at offset {offset}"
            )

            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=filename, Range=range_header
            )

            content = response["Body"].read()
            logger.info(f"Successfully fetched {len(content)} bytes")
            return content

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(
                f"S3 client error {error_code}: {e.response['Error']['Message']}"
            )
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching S3 content: {e}")
            return None
