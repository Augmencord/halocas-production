"""HALOCAS Object Storage Service.

Provides production-grade Cloudflare R2 (S3-compatible) object storage integration
for industrial safety video clips and incident recordings. Handles authenticated
boto3 client configuration, automatic MIME content-type detection, chunked upload
progress logging, presigned temporary playback URL synthesis, object deletion,
and structured incident key formatting (`incidents/{YYYY}/{MM}/{DD}/{id}_{cam}.mp4`).
"""

from __future__ import annotations

import mimetypes
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("halocas.services.storage")

# Standard incident key regex: incidents/YYYY/MM/DD/<incident_id>_<camera_id>.mp4
OBJECT_KEY_PATTERN = re.compile(
    r"^incidents/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<incident_id>\d+)_(?P<camera_id>[a-zA-Z0-9_\-]+)\.(?P<ext>[a-zA-Z0-9]+)$"
)


class StorageError(Exception):
    """Base exception for storage subsystem operational errors."""


class StorageUploadError(StorageError):
    """Raised when an asset fails to upload to the remote bucket."""


class StorageDeleteError(StorageError):
    """Raised when an object fails to delete from the remote bucket."""


class InvalidObjectKeyError(StorageError):
    """Raised when an invalid object key or incident directory path is provided."""


class UploadProgressLogger:
    """Callable progress hook tracking and logging multi-part upload milestones."""

    def __init__(self, filename: str, total_bytes: int) -> None:
        """Initialize upload progress tracker.

        Args:
            filename: Local file path being transferred.
            total_bytes: Total file size in bytes.
        """
        self.filename = filename
        self.total_bytes = max(total_bytes, 1)
        self.transferred_bytes = 0
        self._last_logged_percentage = -1

    def __call__(self, bytes_amount: int) -> None:
        """Callback executed by boto3 on chunk transfer."""
        self.transferred_bytes += bytes_amount
        percentage = int((self.transferred_bytes / self.total_bytes) * 100)

        # Log at 25%, 50%, 75%, and 100% intervals
        if percentage >= self._last_logged_percentage + 25 or percentage == 100:
            self._last_logged_percentage = percentage
            logger.debug(
                "Upload progress for %s: %d%% (%d/%d bytes)",
                self.filename,
                percentage,
                self.transferred_bytes,
                self.total_bytes,
            )


class StorageService:
    """Storage client managing incident video assets on Cloudflare R2 / S3."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
        public_url_base: str | None = None,
        client: Any = None,
    ) -> None:
        """Initialize StorageService with R2 credentials and bucket configuration.

        Args:
            endpoint_url: Cloudflare R2 S3 endpoint URL.
            access_key_id: Cloudflare R2 access key ID.
            secret_access_key: Cloudflare R2 secret access key.
            bucket_name: Destination storage bucket designation.
            public_url_base: Optional CDN/custom domain for public access URLs.
            client: Optional pre-configured boto3 client (useful for unit testing).
        """
        settings = get_settings()
        self.endpoint_url = endpoint_url or settings.R2_ENDPOINT or "https://r2.cloudflarestorage.com"
        self.access_key_id = access_key_id or settings.R2_ACCESS_KEY or "mock_access_key"
        self.secret_access_key = secret_access_key or settings.R2_SECRET_KEY or "mock_secret_key"
        self.bucket_name = bucket_name or settings.R2_BUCKET or "halocas-clips"
        self.public_url_base = public_url_base

        if client is not None:
            self.s3_client = client
        else:
            # Cloudflare R2 requires custom endpoint, signature v4, and path-style addressing
            boto_config = Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                s3={"addressing_style": "path"},
            )
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=boto_config,
                region_name="auto",
            )

        logger.info(
            "StorageService initialized for bucket '%s' with endpoint '%s'",
            self.bucket_name,
            self.endpoint_url,
        )

    @staticmethod
    def build_object_key(
        incident_id: int,
        camera_id: str,
        timestamp: datetime | None = None,
        extension: str = "mp4",
    ) -> str:
        """Construct standard partitioned storage path for an incident clip.

        Format: `incidents/{YYYY}/{MM}/{DD}/{incident_id}_{camera_id}.{ext}`

        Args:
            incident_id: Unique database primary key of safety breach.
            camera_id: Stream identifier (e.g. 'front', 'rear').
            timestamp: Incident event datetime. Defaults to UTC now if None.
            extension: Video container extension without leading period.

        Returns:
            str: Partitioned hierarchical object key.
        """
        dt = timestamp or datetime.now(UTC)
        clean_cam = re.sub(r"[^a-zA-Z0-9]+", "_", camera_id.strip().lower()).strip("_")
        ext = extension.lstrip(".").lower()
        return f"incidents/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/{incident_id}_{clean_cam}.{ext}"

    @staticmethod
    def validate_object_key(object_key: str) -> bool:
        """Validate whether an S3 object key conforms to HALOCAS incident format.

        Args:
            object_key: S3 object key string.

        Returns:
            bool: True if key adheres to `incidents/YYYY/MM/DD/<id>_<cam>.<ext>`.
        """
        return bool(OBJECT_KEY_PATTERN.match(object_key))

    def upload_clip(self, local_path: str, object_key: str) -> str:
        """Upload a local video file to Cloudflare R2 and return its public URL.

        Detects content-type automatically, executes chunked progress tracking,
        and provides full error isolation.

        Args:
            local_path: Filesystem path to source video file.
            object_key: Target object key in the R2 bucket.

        Returns:
            str: Publicly reachable URL pointing to the uploaded asset.

        Raises:
            FileNotFoundError: If the local file does not exist or is empty.
            StorageUploadError: If boto3 upload execution fails.
        """
        file_path = Path(local_path).resolve()
        if not file_path.is_file():
            logger.error("Upload failed: source clip not found at path: %s", local_path)
            raise FileNotFoundError(f"Source file not found: {local_path}")

        file_size = file_path.stat().st_size
        if file_size == 0:
            logger.error("Upload failed: source clip at %s is 0 bytes", local_path)
            raise StorageUploadError(f"Cannot upload empty file: {local_path}")

        # Automatic MIME Content-Type detection
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = "video/mp4"

        progress_callback = UploadProgressLogger(
            filename=file_path.name,
            total_bytes=file_size,
        )

        logger.info(
            "Uploading incident clip %s (%d bytes, type=%s) to R2 key '%s'",
            file_path.name,
            file_size,
            content_type,
            object_key,
        )

        try:
            self.s3_client.upload_file(
                Filename=str(file_path),
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs={
                    "ContentType": content_type,
                },
                Callback=progress_callback,
            )
            logger.info("Successfully uploaded clip to R2: %s", object_key)

            if self.public_url_base:
                return f"{self.public_url_base.rstrip('/')}/{object_key.lstrip('/')}"

            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{object_key.lstrip('/')}"

        except (ClientError, BotoCoreError, Exception) as exc:
            logger.error(
                "boto3 failed to upload clip %s to key '%s': %s",
                local_path,
                object_key,
                exc,
            )
            raise StorageUploadError(f"Failed to upload clip to R2: {exc}") from exc

    def generate_presigned_url(
        self, object_key: str, expiry_seconds: int = 3600
    ) -> str:
        """Generate a time-limited presigned URL for secure access to private clips.

        Args:
            object_key: Target object key in the R2 bucket.
            expiry_seconds: URL lifetime in seconds (default: 3600s = 1 hour).

        Returns:
            str: Signed URL permitting authenticated read access.

        Raises:
            StorageError: If presigned URL synthesis fails.
        """
        try:
            url: str = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key,
                },
                ExpiresIn=expiry_seconds,
            )
            logger.debug(
                "Generated presigned URL for key '%s' (expires in %ds)",
                object_key,
                expiry_seconds,
            )
            return url

        except (ClientError, BotoCoreError, Exception) as exc:
            logger.error(
                "Failed to generate presigned URL for key '%s': %s",
                object_key,
                exc,
            )
            raise StorageError(f"Presigned URL generation failed: {exc}") from exc

    def delete_clip(self, object_key: str) -> bool:
        """Remove a clip from the R2 storage bucket.

        Args:
            object_key: Target object key to delete.

        Returns:
            bool: True if deletion was acknowledged by R2, False otherwise.
        """
        try:
            logger.info("Deleting object from R2 bucket '%s': %s", self.bucket_name, object_key)
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
            logger.info("Successfully deleted R2 object: %s", object_key)
            return True

        except (ClientError, BotoCoreError, Exception) as exc:
            logger.error("Failed to delete object '%s' from R2: %s", object_key, exc)
            return False

    def list_clips(self, prefix: str = "") -> list[dict[str, Any]]:
        """List stored clips matching an optional directory prefix with metadata.

        Args:
            prefix: Key prefix filter (e.g. 'incidents/2026/09/').

        Returns:
            list[dict[str, Any]]: List of metadata dictionaries containing
                'key', 'size', 'last_modified', and 'etag'.
        """
        try:
            logger.debug("Listing R2 objects with prefix '%s' in bucket '%s'", prefix, self.bucket_name)
            paginator = self.s3_client.get_paginator("list_objects_v2")
            results: list[dict[str, Any]] = []

            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                contents = page.get("Contents", [])
                for item in contents:
                    results.append(
                        {
                            "key": item.get("Key", ""),
                            "size": item.get("Size", 0),
                            "last_modified": item.get("LastModified"),
                            "etag": item.get("ETag", "").strip('"'),
                        }
                    )

            logger.info("Listed %d clips matching prefix '%s'", len(results), prefix)
            return results

        except (ClientError, BotoCoreError, Exception) as exc:
            logger.error("Failed to list objects with prefix '%s': %s", prefix, exc)
            return []
