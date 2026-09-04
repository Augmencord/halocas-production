"""Unit tests for the HALOCAS Cloudflare R2 / S3 StorageService.

Validates object key construction and regex validation, automatic MIME content-type
detection, upload success and failure handling, presigned URL generation, deletion,
and paginated clip listings with mocked boto3 S3 client.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.services.storage import (
    StorageError,
    StorageService,
    StorageUploadError,
    UploadProgressLogger,
)


@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Create a mock boto3 S3 client with standard method signatures."""
    client = MagicMock()
    return client


@pytest.fixture
def storage_service(mock_s3_client: MagicMock) -> StorageService:
    """Initialize StorageService with injected mock boto3 client."""
    return StorageService(
        endpoint_url="https://test-account.r2.cloudflarestorage.com",
        access_key_id="test_key",
        secret_access_key="test_secret",
        bucket_name="halocas-test-clips",
        public_url_base="https://cdn.halocas.safety",
        client=mock_s3_client,
    )


def test_object_key_generation_and_validation() -> None:
    """Verify standard partitioned key formatting and regex schema validation."""
    ts = datetime(2026, 9, 4, 15, 30, 0, tzinfo=UTC)
    key = StorageService.build_object_key(
        incident_id=142,
        camera_id="Front-Cabin",
        timestamp=ts,
    )
    assert key == "incidents/2026/09/04/142_front_cabin.mp4"
    assert StorageService.validate_object_key(key) is True

    # Valid alternatives
    assert StorageService.validate_object_key("incidents/2025/12/31/1_rear.mp4") is True
    assert StorageService.validate_object_key("incidents/2026/01/01/9999_cam_01.mkv") is True

    # Invalid keys
    assert StorageService.validate_object_key("invalid/path/file.mp4") is False
    assert StorageService.validate_object_key("incidents/2026/9/4/1_front.mp4") is False  # Missing 0 padding
    assert StorageService.validate_object_key("incidents/2026/09/04/clip.mp4") is False  # Missing ID


def test_upload_clip_success(
    storage_service: StorageService, mock_s3_client: MagicMock, tmp_path: Path
) -> None:
    """Verify successful upload of a local video file with metadata and public URL generation."""
    test_file = tmp_path / "incident_clip.mp4"
    test_file.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 1024)

    key = "incidents/2026/09/04/101_front.mp4"
    public_url = storage_service.upload_clip(str(test_file), key)

    assert public_url == f"https://cdn.halocas.safety/{key}"
    mock_s3_client.upload_file.assert_called_once()
    call_kwargs = mock_s3_client.upload_file.call_args[1]

    assert call_kwargs["Bucket"] == "halocas-test-clips"
    assert call_kwargs["Key"] == key
    assert call_kwargs["Filename"] == str(test_file.resolve())
    assert call_kwargs["ExtraArgs"]["ContentType"] == "video/mp4"
    assert call_kwargs["Callback"] is not None


def test_upload_clip_fallback_url_construction(mock_s3_client: MagicMock, tmp_path: Path) -> None:
    """Verify fallback public URL when public_url_base is not set."""
    service = StorageService(
        endpoint_url="https://account.r2.cloudflarestorage.com",
        bucket_name="my-bucket",
        client=mock_s3_client,
    )
    test_file = tmp_path / "test.mp4"
    test_file.write_bytes(b"dummy video data")

    key = "incidents/2026/09/04/1_cam.mp4"
    url = service.upload_clip(str(test_file), key)
    assert url == "https://account.r2.cloudflarestorage.com/my-bucket/incidents/2026/09/04/1_cam.mp4"


def test_upload_clip_file_not_found(storage_service: StorageService) -> None:
    """Verify FileNotFoundError when targeting non-existent local file."""
    with pytest.raises(FileNotFoundError, match="Source file not found"):
        storage_service.upload_clip("non_existent_file.mp4", "incidents/key.mp4")


def test_upload_clip_empty_file(storage_service: StorageService, tmp_path: Path) -> None:
    """Verify rejection of 0-byte files."""
    empty_file = tmp_path / "empty.mp4"
    empty_file.touch()

    with pytest.raises(StorageUploadError, match="Cannot upload empty file"):
        storage_service.upload_clip(str(empty_file), "incidents/key.mp4")


def test_upload_clip_boto3_failure(
    storage_service: StorageService, mock_s3_client: MagicMock, tmp_path: Path
) -> None:
    """Verify exception handling when boto3 encounters AWS client errors."""
    test_file = tmp_path / "error_file.mp4"
    test_file.write_bytes(b"data")

    mock_s3_client.upload_file.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Invalid credentials"}},
        "UploadFile",
    )

    with pytest.raises(StorageUploadError, match="Failed to upload clip to R2"):
        storage_service.upload_clip(str(test_file), "incidents/key.mp4")


def test_generate_presigned_url_success(
    storage_service: StorageService, mock_s3_client: MagicMock
) -> None:
    """Verify generation of presigned time-limited access URLs."""
    mock_s3_client.generate_presigned_url.return_value = (
        "https://r2.example.com/bucket/key?X-Amz-Signature=xyz"
    )

    key = "incidents/2026/09/04/101_front.mp4"
    url = storage_service.generate_presigned_url(key, expiry_seconds=1800)

    assert "X-Amz-Signature=xyz" in url
    mock_s3_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "halocas-test-clips", "Key": key},
        ExpiresIn=1800,
    )


def test_generate_presigned_url_failure(
    storage_service: StorageService, mock_s3_client: MagicMock
) -> None:
    """Verify error wrapping when presigned URL generation fails."""
    mock_s3_client.generate_presigned_url.side_effect = ClientError(
        {"Error": {"Code": "SignatureDoesNotMatch", "Message": "Invalid key"}},
        "GeneratePresignedUrl",
    )

    with pytest.raises(StorageError, match="Presigned URL generation failed"):
        storage_service.generate_presigned_url("incidents/invalid.mp4")


def test_delete_clip(storage_service: StorageService, mock_s3_client: MagicMock) -> None:
    """Verify object deletion operations under normal and error conditions."""
    key = "incidents/2026/09/04/101_front.mp4"

    # Success case
    assert storage_service.delete_clip(key) is True
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket="halocas-test-clips",
        Key=key,
    )

    # Failure case
    mock_s3_client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}},
        "DeleteObject",
    )
    assert storage_service.delete_clip(key) is False


def test_list_clips_paginated(
    storage_service: StorageService, mock_s3_client: MagicMock
) -> None:
    """Verify paginated listing and metadata mapping."""
    mock_paginator = MagicMock()
    mock_s3_client.get_paginator.return_value = mock_paginator

    dt = datetime(2026, 9, 4, 12, 0, 0, tzinfo=UTC)
    mock_paginator.paginate.return_value = [
        {
            "Contents": [
                {
                    "Key": "incidents/2026/09/04/1_front.mp4",
                    "Size": 1048576,
                    "LastModified": dt,
                    "ETag": '"etag123"',
                },
                {
                    "Key": "incidents/2026/09/04/1_rear.mp4",
                    "Size": 2097152,
                    "LastModified": dt,
                    "ETag": '"etag456"',
                },
            ]
        }
    ]

    clips = storage_service.list_clips(prefix="incidents/2026/09/04/")

    assert len(clips) == 2
    assert clips[0]["key"] == "incidents/2026/09/04/1_front.mp4"
    assert clips[0]["size"] == 1048576
    assert clips[0]["etag"] == "etag123"
    assert clips[1]["key"] == "incidents/2026/09/04/1_rear.mp4"
    assert clips[1]["size"] == 2097152

    # Test error handling returns empty list
    mock_s3_client.get_paginator.side_effect = ClientError(
        {"Error": {"Code": "InternalError", "Message": "S3 failure"}},
        "GetPaginator",
    )
    assert storage_service.list_clips() == []


def test_upload_progress_logger() -> None:
    """Verify UploadProgressLogger milestone calculations."""
    progress = UploadProgressLogger(filename="clip.mp4", total_bytes=1000)

    # 100 bytes (10%)
    progress(100)
    assert progress.transferred_bytes == 100
    assert progress._last_logged_percentage == -1  # Below 25% threshold

    # 200 more bytes (total 300 = 30%)
    progress(200)
    assert progress.transferred_bytes == 300
    assert progress._last_logged_percentage == 30  # Crosses 25%

    # 700 more bytes (total 1000 = 100%)
    progress(700)
    assert progress.transferred_bytes == 1000
    assert progress._last_logged_percentage == 100
