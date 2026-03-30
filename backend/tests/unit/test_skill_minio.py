"""TDD tests for MinIO-based SkillStorage.

Tests cover:
- SkillStorage.store_package: uploads ZIP to MinIO
- SkillStorage.get_package: retrieves ZIP bytes from MinIO
- SkillStorage.delete_package: removes ZIP from MinIO
- Bucket creation on init
"""
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.services.skill.errors import SkillStorageError


class TestSkillStorage:
    """Tests for SkillStorage MinIO operations."""

    def _make_mock_client(self):
        """Create a mock MinIO client."""
        client = MagicMock()
        client.bucket_exists.return_value = False
        return client

    def test_ensure_bucket_called_on_init(self):
        from app.services.skill.storage import SkillStorage

        client = self._make_mock_client()
        storage = SkillStorage(client, bucket="test-bucket")
        client.bucket_exists.assert_called_once_with("test-bucket")
        client.make_bucket.assert_called_once_with("test-bucket")

    def test_ensure_bucket_not_created_if_exists(self):
        from app.services.skill.storage import SkillStorage

        client = self._make_mock_client()
        client.bucket_exists.return_value = True
        storage = SkillStorage(client, bucket="test-bucket")
        client.make_bucket.assert_not_called()

    def test_store_package_returns_key(self):
        from app.services.skill.storage import SkillStorage

        client = self._make_mock_client()
        storage = SkillStorage(client, bucket="skill-packages")

        data = b"fake zip data"
        key = storage.store_package("weather", "1.0.0", data)

        assert key == "weather/1.0.0.zip"
        client.put_object.assert_called_once()
        args, kwargs = client.put_object.call_args
        assert args[0] == "skill-packages"
        assert args[1] == "weather/1.0.0.zip"

    def test_get_package_returns_bytes(self):
        from app.services.skill.storage import SkillStorage

        client = self._make_mock_client()
        expected_data = b"retrieved zip data"
        mock_response = MagicMock()
        mock_response.read.return_value = expected_data
        client.get_object.return_value = mock_response

        storage = SkillStorage(client, bucket="skill-packages")
        result = storage.get_package("weather", "1.0.0")

        assert result == expected_data
        client.get_object.assert_called_once_with("skill-packages", "weather/1.0.0.zip")
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()

    def test_delete_package_calls_remove_object(self):
        from app.services.skill.storage import SkillStorage

        client = self._make_mock_client()
        storage = SkillStorage(client, bucket="skill-packages")
        storage.delete_package("weather", "1.0.0")

        client.remove_object.assert_called_once_with("skill-packages", "weather/1.0.0.zip")

    def test_store_package_raises_on_error(self):
        from app.services.skill.storage import SkillStorage

        client = self._make_mock_client()
        client.put_object.side_effect = Exception("upload failed")
        storage = SkillStorage(client, bucket="skill-packages")

        with pytest.raises(SkillStorageError, match="upload"):
            storage.store_package("weather", "1.0.0", b"data")

    def test_get_package_raises_on_error(self):
        from app.services.skill.storage import SkillStorage

        client = self._make_mock_client()
        client.get_object.side_effect = Exception("download failed")
        storage = SkillStorage(client, bucket="skill-packages")

        with pytest.raises(SkillStorageError, match="download"):
            storage.get_package("weather", "1.0.0")

    def test_delete_package_raises_on_error(self):
        from app.services.skill.storage import SkillStorage

        client = self._make_mock_client()
        client.remove_object.side_effect = Exception("delete failed")
        storage = SkillStorage(client, bucket="skill-packages")

        with pytest.raises(SkillStorageError, match="delete"):
            storage.delete_package("weather", "1.0.0")
