"""MinIO object storage service for file uploads and downloads."""

import os
import logging
from typing import Optional
from datetime import timedelta

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    Minio = None  # type: ignore
    S3Error = Exception  # type: ignore

logger = logging.getLogger(__name__)

# Default bucket names
EXPORT_BUCKET = "exports"
PUBLIC_BUCKET = "public"


class MinioService:
    """Service for uploading and downloading files from MinIO."""

    def __init__(self):
        self.client = None
        self.bucket = EXPORT_BUCKET
        self.presigned_expiry = timedelta(days=30)
        self._initialize()

    def _initialize(self):
        """Initialize MinIO client from environment variables."""
        if not MINIO_AVAILABLE:
            logger.warning("minio package not installed, skipping initialization")
            return

        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY")
        secret_key = os.getenv("MINIO_SECRET_KEY")

        if not access_key or not secret_key:
            logger.warning("MINIO_ACCESS_KEY or MINIO_SECRET_KEY not set, MinIO disabled")
            return

        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._ensure_buckets()

    def _ensure_buckets(self):
        """Create buckets if they don't exist."""
        if not self.client:
            return

        for bucket in [EXPORT_BUCKET, PUBLIC_BUCKET]:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"Created bucket: {bucket}")
            except S3Error as e:
                logger.error(f"Failed to create bucket {bucket}: {e}")

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file to MinIO and return the download URL.

        Args:
            file_bytes: Raw file content
            filename: Object key (path + filename)
            content_type: MIME type of the file

        Returns:
            Full URL to access the file
        """
        if not self.client:
            raise RuntimeError("MinIO client not initialized")

        # Generate object name
        object_name = filename.lstrip("/")
        if not object_name:
            raise ValueError("Filename cannot be empty")

        # Upload
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                data=file_bytes,
                length=len(file_bytes),
                content_type=content_type,
            )
        except S3Error as e:
            logger.error(f"Failed to upload {object_name}: {e}")
            raise

        # Build and return download URL
        url = self._get_download_url(object_name)
        logger.info(f"Uploaded {object_name} → {url}")
        return url

    def generate_presigned_url(self, filename: str, expires: Optional[timedelta] = None) -> str:
        """Generate a presigned URL for downloading a file.

        Args:
            filename: Object key in MinIO
            expires: URL expiration time (default: 30 days)

        Returns:
            Presigned download URL
        """
        if not self.client:
            raise RuntimeError("MinIO client not initialized")

        try:
            url = self.client.presigned_get_object(
                self.bucket,
                filename.lstrip("/"),
                expires=expires or self.presigned_expiry,
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {filename}: {e}")
            raise

    def delete_file(self, filename: str) -> bool:
        """Delete a file from MinIO.

        Args:
            filename: Object key to delete

        Returns:
            True if deleted successfully
        """
        if not self.client:
            return False

        try:
            self.client.remove_object(self.bucket, filename.lstrip("/"))
            return True
        except S3Error as e:
            logger.error(f"Failed to delete {filename}: {e}")
            return False

    def _get_download_url(self, object_name: str) -> str:
        """Build the public download URL for an object."""
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        protocol = "https" if secure else "http"

        # Handle endpoint format (may include port)
        host = endpoint
        if host.startswith("http://") or host.startswith("https://"):
            # Remove protocol prefix
            host = host.split("://", 1)[1]

        return f"{protocol}://{host}/{self.bucket}/{object_name.lstrip('/')}"

    def is_available(self) -> bool:
        """Check if MinIO service is available."""
        return self.client is not None


# Singleton instance
_minio_service: Optional[MinioService] = None


def get_minio_service() -> Optional[MinioService]:
    """Get the global MinIO service instance."""
    global _minio_service
    if _minio_service is None:
        _minio_service = MinioService()
    return _minio_service
