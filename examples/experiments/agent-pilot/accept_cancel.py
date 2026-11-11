"""Held-out acceptance, derived only from README contract (explicit pytest path)."""

import pytest
from api import API
from client import Client
from domain import Order
from store import Store


def setup():
    store = Store(
        [
            Order("a", "u", 125),
            Order("b", "u", 70),
            Order("s", "u", 90, "shipped"),
            Order("v", "v", 45),
        ]
    )
    return store, API(store)


def test_refund_replay_and_cross_instance():
    store, api = setup()
    expected = {"id": "a", "state": "cancelled", "refunded": 125}
    assert Client(api, "u").cancel("a", "k") == expected
    assert API(store).cancel("u", "a", "k") == (200, expected)
    assert store.refunds == [("a", 125)]
    assert api.get("u", "a") == (200, {"id": "a", "state": "cancelled", "cents": 125})
    assert api.cancel("u", "a", "other")[0] == 409
    assert api.cancel("u", "b", "k")[0] == 409
    assert api.cancel("u", "missing", "k")[0] == 409
    assert api.cancel("v", "v", "k")[0] == 200
    assert store.refunds == [("a", 125), ("v", 45)]


@pytest.mark.parametrize("order,status", [("missing", 404), ("v", 404), ("s", 409)])
def test_failure_does_not_reserve(order, status):
    store, api = setup()
    assert api.cancel("u", order, "retry")[0] == status
    assert store.refunds == []
    assert api.cancel("u", "a", "retry")[0] == 200
    assert store.get("s").state == "shipped"


@pytest.mark.parametrize("key", ["", None, 1, False, []])
def test_invalid_keys(key):
    store, api = setup()
    assert api.cancel("u", "a", key)[0] == 400
    assert store.refunds == []
    assert store.get("a").state == "paid"


def test_client_error():
    _, api = setup()
    with pytest.raises(ValueError) as exc:
        Client(api, "u").cancel("s", "k")
    assert exc.value.args == (409,)
