"""JSON Schema validation."""

from dataclasses import dataclass
from typing import Any

import jsonschema
from jsonschema import Draft7Validator, validators

from docagentline.observability import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationError:
    """Validation error detail."""

    json_path: str
    message: str


@dataclass
class ValidationResult:
    """Validation result container."""

    is_valid: bool
    errors: list[ValidationError]


class SchemaValidator:
    """JSON Schema validator."""

    def __init__(self):
        # Extend validator to set default values
        def set_defaults(validator, properties, instance, schema):
            for property, subschema in properties.items():
                if "default" in subschema:
                    instance.setdefault(property, subschema["default"])

            for error in Draft7Validator.VALIDATORS["properties"](
                validator, properties, instance, schema
            ):
                yield error

        all_validators = dict(Draft7Validator.VALIDATORS)
        all_validators["properties"] = set_defaults
        self.ValidatorWithDefaults = validators.create(
            meta_schema=Draft7Validator.META_SCHEMA,
            validators=all_validators,
        )

    def validate(self, data: Any, schema: dict[str, Any]) -> ValidationResult:
        """Validate data against JSON schema.

        Args:
            data: Data to validate
            schema: JSON schema

        Returns:
            ValidationResult with errors if any
        """
        validator = self.ValidatorWithDefaults(schema)
        errors = []

        for error in sorted(validator.iter_errors(data), key=str):
            json_path = "$.{}".format(".".join(str(p) for p in error.path))
            errors.append(
                ValidationError(
                    json_path=json_path,
                    message=error.message,
                )
            )

        is_valid = len(errors) == 0

        if not is_valid:
            logger.debug(
                "Schema validation failed",
                extra={"error_count": len(errors), "errors": [e.message for e in errors[:5]]},
            )

        return ValidationResult(is_valid=is_valid, errors=errors)
