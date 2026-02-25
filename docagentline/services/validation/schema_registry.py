"""Schema registry for loading and caching JSON schemas."""

import json
from pathlib import Path
from typing import Any

from docagentline.config import get_settings
from docagentline.observability import get_logger
from docagentline.utils.errors import SchemaRegistryError

logger = get_logger(__name__)


class SchemaRegistry:
    """Schema registry for managing JSON schemas."""

    def __init__(self):
        self.settings = get_settings()
        self._cache: dict[str, dict[str, Any]] = {}

    def get_schema(self, schema_version: str) -> dict[str, Any]:
        """Get schema by version.

        Args:
            schema_version: Schema version identifier (e.g., 'invoice_v1')

        Returns:
            JSON schema dictionary

        Raises:
            SchemaRegistryError: If schema not found or invalid
        """
        if schema_version in self._cache:
            return self._cache[schema_version]

        schema_path = self.settings.get_schema_registry_path() / f"{schema_version}.json"

        if not schema_path.exists():
            raise SchemaRegistryError(
                f"Schema not found: {schema_version}",
                details={"schema_version": schema_version, "path": str(schema_path)},
            )

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)

            # Basic validation that it's a valid schema
            if not isinstance(schema, dict):
                raise SchemaRegistryError(
                    f"Invalid schema format: {schema_version}",
                    details={"schema_version": schema_version},
                )

            self._cache[schema_version] = schema
            logger.info(
                "Loaded schema",
                extra={"schema_version": schema_version, "path": str(schema_path)},
            )

            return schema

        except json.JSONDecodeError as e:
            raise SchemaRegistryError(
                f"Invalid JSON in schema: {schema_version}",
                details={"schema_version": schema_version, "error": str(e)},
            )
        except Exception as e:
            raise SchemaRegistryError(
                f"Failed to load schema: {schema_version}",
                details={"schema_version": schema_version, "error": str(e)},
            )

    def list_schemas(self) -> list[str]:
        """List all available schema versions.

        Returns:
            List of schema version identifiers
        """
        schema_dir = self.settings.get_schema_registry_path()

        if not schema_dir.exists():
            return []

        schemas = []
        for path in schema_dir.glob("*.json"):
            schema_version = path.stem
            schemas.append(schema_version)

        return sorted(schemas)

    def clear_cache(self):
        """Clear schema cache."""
        self._cache.clear()
