from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ItemResponse(BaseModel):
    """Response for a portfolio item (project, skill, ...). The JSON id key is `_id`, as the frontend expects."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(serialization_alias="_id")
    user_id: UUID
