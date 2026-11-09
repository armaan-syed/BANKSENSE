from __future__ import annotations

VALIDATION_ERROR = "VALIDATION_ERROR"
UNKNOWN_MODEL = "UNKNOWN_MODEL"
MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
INFERENCE_ERROR = "INFERENCE_ERROR"
NOT_FOUND = "NOT_FOUND"


class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field

    def to_dict(self) -> dict:
        detail = {"code": self.code, "message": self.message}
        if self.field is not None:
            detail["field"] = self.field
        return {"error": detail}
