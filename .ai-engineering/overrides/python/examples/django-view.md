# Example — Django view (DRF)

A typed, validated, paginated list endpoint. Demonstrates: pydantic-
style serializers, parameterised ORM, structured error responses.

```python
# markets/views.py
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from markets.models import Market
from markets.serializers import MarketSerializer


class MarketViewSet(ReadOnlyModelViewSet):
    serializer_class = MarketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ORM parameterises every value; never f-string SQL.
        qs = Market.objects.select_related("issuer").only(
            "id", "symbol", "last_price", "issuer__name"
        )
        symbol = self.request.query_params.get("symbol")
        if symbol:
            qs = qs.filter(symbol__iexact=symbol)
        return qs.order_by("symbol")

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        if page is None:
            return Response(
                {"error": "pagination_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
```

## TDD pairing

```python
# markets/tests/test_views.py
import pytest
from rest_framework.test import APIClient

from markets.models import Market


@pytest.fixture
def client(db, django_user_model):
    user = django_user_model.objects.create_user("alice")
    api = APIClient()
    api.force_authenticate(user)
    return api


def test_list_returns_only_matching_symbol(client, db):
    Market.objects.create(symbol="BTC", last_price=65000)
    Market.objects.create(symbol="ETH", last_price=3300)
    res = client.get("/api/markets/?symbol=btc")
    assert res.status_code == 200
    assert {row["symbol"] for row in res.data["results"]} == {"BTC"}
```
