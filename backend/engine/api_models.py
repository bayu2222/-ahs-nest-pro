"""Pydantic DTOs for the HTTP API (translation boundary to the engine)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ShapeInput(BaseModel):
    id: Optional[str] = None
    type: str
    width: float = 0.0
    height: float = 0.0
    points: Optional[List[List[float]]] = None
    original_rotation: float = 0.0


class SettingsInput(BaseModel):
    media_width: float = 120.0
    media_height: Optional[float] = None
    height_mode: str = "auto"  # "auto" | "fixed"
    spacing: float = 0.3
    rotation_step: float = 5.0
    allow_rotation: bool = True
    max_angle: float = 360.0
    algorithm: str = "bottom-left-fill"


class GenerateRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=300)
    seed: int = 42
    types: Optional[List[str]] = None


class NestRequest(BaseModel):
    objects: List[ShapeInput]
    settings: SettingsInput = SettingsInput()
    debug: bool = False


class BenchmarkRequest(BaseModel):
    counts: List[int] = [10, 20, 50, 100]
    settings: SettingsInput = SettingsInput()
    seed: int = 42
