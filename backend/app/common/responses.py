"""API response envelopes from `AI_BUILD_SPEC.md` section 24."""

from pydantic import BaseModel, Field


class DataResponse[T](BaseModel):
    data: T


class ErrorDetail(BaseModel):
    code: str = Field(examples=["RESOURCE_NOT_FOUND"])
    message: str = Field(examples=["Project not found"])


class ErrorResponse(BaseModel):
    error: ErrorDetail
