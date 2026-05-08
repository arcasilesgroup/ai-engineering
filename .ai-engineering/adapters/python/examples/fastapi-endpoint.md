# Example — FastAPI endpoint

A typed POST endpoint. Demonstrates: pydantic v2 validation, dependency
injection, structured error responses, async handlers.

```python
# markets/api.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

from markets.repository import MarketRepository, get_market_repo

router = APIRouter(prefix="/markets", tags=["markets"])


class CreateMarketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=10, pattern=r"^[A-Z]+$")
    last_price: float = Field(gt=0)


class MarketResponse(BaseModel):
    id: str
    symbol: str
    last_price: float


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_market(
    payload: CreateMarketRequest,
    repo: Annotated[MarketRepository, Depends(get_market_repo)],
) -> MarketResponse:
    if await repo.exists(symbol=payload.symbol):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "symbol_taken", "symbol": payload.symbol},
        )
    market = await repo.create(symbol=payload.symbol, last_price=payload.last_price)
    return MarketResponse(
        id=market.id, symbol=market.symbol, last_price=market.last_price
    )
```

## TDD pairing

```python
# markets/tests/test_api.py
import pytest
from httpx import AsyncClient, ASGITransport

from markets.app import app


@pytest.mark.asyncio
async def test_rejects_invalid_symbol():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        res = await client.post("/markets", json={"symbol": "", "last_price": 1.0})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_creates_market_and_returns_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        res = await client.post(
            "/markets", json={"symbol": "BTC", "last_price": 65000.0}
        )
    assert res.status_code == 201
    assert res.json()["symbol"] == "BTC"
```
