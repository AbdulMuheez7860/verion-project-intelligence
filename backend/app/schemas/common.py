from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    """Base schema — serializes to camelCase for the React frontend."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        serialize_by_alias=True,
        from_attributes=True,
    )


class MessageResponse(APIModel):
    message: str