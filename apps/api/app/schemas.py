"""HTTP request and response schemas for game rooms."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateRoomRequest(BaseModel):
    """Describe a new private game room."""

    model_config = ConfigDict(populate_by_name=True)

    nickname: str = Field(min_length=2, max_length=24)
    player_count: Literal[2, 3] = Field(
        default=2,
        alias="playerCount",
    )
    bot_count: int = Field(
        default=0,
        ge=0,
        le=2,
        alias="botCount",
    )


class JoinRoomRequest(BaseModel):
    """Describe a player joining an existing room."""

    nickname: str = Field(min_length=2, max_length=24)
