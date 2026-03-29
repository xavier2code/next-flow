import uuid
from datetime import datetime, timezone

import pytest

from app.schemas.envelope import (
    PaginationMeta,
    encode_cursor,
    decode_cursor,
)


class TestEncodeDecodeCursor:
    def test_roundtrip(self):
        ts = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)
        item_id = str(uuid.uuid4())
        encoded = encode_cursor(ts, item_id)
        decoded_ts, decoded_id = decode_cursor(encoded)
        assert decoded_ts == ts
        assert decoded_id == item_id

    def test_encode_produces_base64(self):
        ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        item_id = str(uuid.uuid4())
        encoded = encode_cursor(ts, item_id)
        assert isinstance(encoded, str)
        assert "|" not in encoded
        import base64
        base64.urlsafe_b64decode(encoded.encode())

    def test_decode_invalid_base64_raises(self):
        with pytest.raises(Exception):
            decode_cursor("!!!invalid-base64!!!")

    def test_decode_missing_separator_raises(self):
        import base64
        raw = base64.urlsafe_b64encode(b"no-separator-here").decode()
        with pytest.raises(ValueError):
            decode_cursor(raw)


class TestPaginationMeta:
    def test_defaults(self):
        meta = PaginationMeta()
        assert meta.cursor is None
        assert meta.has_more is False

    def test_with_values(self):
        meta = PaginationMeta(cursor="abc123", has_more=True)
        assert meta.cursor == "abc123"
        assert meta.has_more is True
