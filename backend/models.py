from typing import List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image data")


class DepopItem(BaseModel):
    id: int
    external_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    distance: Optional[float] = None
    redirect_url: Optional[str] = None


class SearchResponse(BaseModel):
    items: List[DepopItem]
