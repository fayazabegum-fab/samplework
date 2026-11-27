"""Write unmodified Pub/Sub payloads and transport metadata to BigQuery."""

from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from google.api_core.exceptions import GoogleAPICallError


class BigQueryWriteError(RuntimeError):
    """Raised when BigQuery rejects or cannot accept a raw message row."""


def build_raw_row(message: Any, ingested_at: datetime) -> dict[str, Any]:
    """Map Pub/Sub bytes and transport metadata to the raw table schema."""
    publish_time = message.publish_time
    if publish_time.tzinfo is None:
        publish_time = publish_time.replace(tzinfo=UTC)
    if ingested_at.tzinfo is None:
        ingested_at = ingested_at.replace(tzinfo=UTC)

    return {
        "payload": base64.b64encode(message.data).decode("ascii"),
        "message_id": message.message_id,
        "publish_time": publish_time.isoformat(),
        "attributes": dict(message.attributes),
        "ingested_at": ingested_at.isoformat(),
    }


class BigQueryWriter:
    """Insert one raw Pub/Sub message into its configured BigQuery table."""

    def __init__(
        self,
        client: Any,
        project_id: str,
        dataset_id: str,
        table_id: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._client = client
        self._table_id = f"{project_id}.{dataset_id}.{table_id}"
        self._clock = clock

    def write(self, message: Any) -> None:
        """Insert a raw message and raise when BigQuery reports a failed row."""
        row = build_raw_row(message, self._clock())
        try:
            errors = self._client.insert_rows_json(self._table_id, [row], row_ids=[None])
        except GoogleAPICallError as error:
            raise BigQueryWriteError("BigQuery streaming insert request failed") from error

        if errors:
            raise BigQueryWriteError(
                f"BigQuery rejected a raw message row for {self._table_id}: {len(errors)} error(s)"
            )
