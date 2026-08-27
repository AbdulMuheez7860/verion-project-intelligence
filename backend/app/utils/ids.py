from typing import Any

from bson import ObjectId


def new_id() -> str:
    return str(ObjectId())


def slugify(value: str) -> str:
    return "-".join(value.lower().strip().split())


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    result = dict(doc)
    if "_id" in result:
        result["id"] = str(result.pop("_id"))
    return result
