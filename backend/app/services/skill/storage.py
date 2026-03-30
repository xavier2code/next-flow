"""MinIO-based skill package storage.

Per D-30: Skill packages stored in MinIO with path pattern {name}/{version}.zip.
"""
from io import BytesIO

from minio import Minio

from app.services.skill.errors import SkillStorageError


class SkillStorage:
    """Manages skill package storage in MinIO."""

    def __init__(self, client: Minio, bucket: str = "skill-packages") -> None:
        self._client = client
        self._bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the bucket if it does not exist."""
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
        except Exception as exc:
            raise SkillStorageError(
                f"Failed to ensure bucket exists: {exc}"
            ) from exc

    def store_package(self, name: str, version: str, data: bytes) -> str:
        """Store a ZIP package in MinIO.

        Args:
            name: Skill name.
            version: Skill version string.
            data: ZIP file bytes.

        Returns:
            The MinIO object key (e.g., "weather/1.0.0.zip").

        Raises:
            SkillStorageError: If upload fails.
        """
        key = f"{name}/{version}.zip"
        try:
            self._client.put_object(
                self._bucket,
                key,
                BytesIO(data),
                len(data),
                content_type="application/zip",
            )
            return key
        except Exception as exc:
            raise SkillStorageError(
                f"Failed to upload package '{key}': {exc}"
            ) from exc

    def get_package(self, name: str, version: str) -> bytes:
        """Retrieve a ZIP package from MinIO.

        Args:
            name: Skill name.
            version: Skill version string.

        Returns:
            ZIP file bytes.

        Raises:
            SkillStorageError: If download fails.
        """
        key = f"{name}/{version}.zip"
        try:
            response = self._client.get_object(self._bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except SkillStorageError:
            raise
        except Exception as exc:
            raise SkillStorageError(
                f"Failed to download package '{key}': {exc}"
            ) from exc

    def delete_package(self, name: str, version: str) -> None:
        """Remove a ZIP package from MinIO.

        Args:
            name: Skill name.
            version: Skill version string.

        Raises:
            SkillStorageError: If deletion fails.
        """
        key = f"{name}/{version}.zip"
        try:
            self._client.remove_object(self._bucket, key)
        except Exception as exc:
            raise SkillStorageError(
                f"Failed to delete package '{key}': {exc}"
            ) from exc
