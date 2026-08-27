from typing import Generic, TypeVar

from fastapi import Query
from pydantic import Field

from app.schemas.common import APIModel

T = TypeVar("T")


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-based)."),
        page_size: int = Query(50, ge=1, le=200, alias="pageSize", description="Items per page."),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(APIModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")
    has_next: bool = Field(serialization_alias="hasNext")

    @classmethod
    def build(cls, items: list[T], *, total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )
