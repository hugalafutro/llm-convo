from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectRequest(BaseModel):
    endpoint_num: int = Field(..., ge=1, le=2)
    endpoint_url: str
    system_prompt: str = ""
    api_key: str = ""
    character_name: str = ""


class ChatRequest(BaseModel):
    prompt: str
    num_exchanges: int = Field(3, ge=1, le=30)


class SetModelRequest(BaseModel):
    endpoint_num: int = Field(..., ge=1, le=2)
    model_id: str


class ClearRequest(BaseModel):
    pass


class Turn(BaseModel):
    speaker: str  # "model1" or "model2"
    content: str


class EndpointConfig(BaseModel):
    url: str = ""
    system_prompt: str = ""
    api_key: str = ""
    model_id: str = "Unknown Model"
    character_name: str = ""


class SessionState(BaseModel):
    endpoint1: EndpointConfig = Field(default_factory=EndpointConfig)
    endpoint2: EndpointConfig = Field(default_factory=EndpointConfig)
    turns: list[Turn] = Field(default_factory=list)
    initial_prompt: str = ""
