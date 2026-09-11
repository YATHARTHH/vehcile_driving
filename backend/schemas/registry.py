import logging
from typing import Any
from pydantic import BaseModel
from backend.schemas.telemetry import RawIngressPayload

logger = logging.getLogger("fleettrack.schemas.registry")


class SchemaCompatibilityError(Exception):
    """Raised when an incoming schema breaks compatibility rules."""
    pass


class SchemaRegistry:
    """
    Schema Registry enforcing BACKWARD compatibility rules on telemetry payloads.
    Rules:
    - Required fields cannot be removed in newer versions.
    - Existing field types cannot change incompatibly.
    - New optional fields with defaults are permitted.
    - Adding new required fields requires a major version bump.
    """
    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}
        # Register default baseline schema
        self.register_schema("v1.0.0", RawIngressPayload)

    def register_schema(self, version: str, model_cls: type[BaseModel]) -> dict[str, Any]:
        schema_dict = model_cls.model_json_schema()
        self._schemas[version] = schema_dict
        logger.info(f"[SchemaRegistry] Registered schema version: {version}")
        return schema_dict

    def get_schema(self, version: str) -> dict[str, Any] | None:
        return self._schemas.get(version)

    def validate_backward_compatibility(
        self,
        base_version: str,
        new_schema: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validates whether new_schema is BACKWARD compatible with base_version.
        """
        base_schema = self._schemas.get(base_version)
        if not base_schema:
            return True, []  # First version or unknown base

        violations: list[str] = []

        base_required = set(base_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        base_props = base_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        # Rule 1: Required fields cannot be removed
        missing_required = base_required - set(new_props.keys())
        if missing_required:
            violations.append(f"Cannot remove required fields from {base_version}: {missing_required}")

        # Rule 2: Cannot introduce new required fields without major version bump
        added_required = new_required - base_required
        if added_required:
            violations.append(f"Cannot add new required fields in backward compatible mode: {added_required}")

        # Rule 3: Existing property types cannot change
        for prop_name, base_prop in base_props.items():
            if prop_name in new_props:
                new_prop = new_props[prop_name]
                base_type = base_prop.get("type")
                new_type = new_prop.get("type")
                if base_type and new_type and base_type != new_type:
                    violations.append(
                        f"Incompatible type change for '{prop_name}': expected {base_type}, got {new_type}"
                    )

        is_compatible = len(violations) == 0
        return is_compatible, violations


# Global Schema Registry singleton
schema_registry = SchemaRegistry()
