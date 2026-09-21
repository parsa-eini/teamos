"""API response envelopes from `AI_BUILD_SPEC.md` section 24."""

from pydantic import BaseModel, Field

from app.common.pagination import PaginationMeta


class DataResponse[T](BaseModel):
    data: T


class CollectionResponse[T](BaseModel):
    data: list[T]
    meta: PaginationMeta


class ErrorDetail(BaseModel):
    code: str = Field(examples=["RESOURCE_NOT_FOUND"])
    message: str = Field(examples=["Project not found"])


class ErrorResponse(BaseModel):
    error: ErrorDetail
