"""Held-out acceptance, derived only from README contract (explicit pytest path)."""

import pytest
from api import API
from client import Client
from domain import Item
from store import Store


def setup():
    store = Store([Item(x, "u" if x in "ace" else "v", x.upper()) for x in "edcba"])
    return store, API(store)


def test_boundaries_and_insertions():
    store, api = setup()
    assert api.page("u", 2) == (
        200,
        {"items": [{"id": "a", "text": "A"}, {"id": "c", "text": "C"}], "next_cursor": "c"},
    )
    store.add(Item("aa", "u", "AA"))
    assert api.page("u", 2, "c") == (
        200,
        {"items": [{"id": "e", "text": "E"}], "next_cursor": None},
    )
    assert api.page("u", 1, "d")[1] == {"items": [{"id": "e", "text": "E"}], "next_cursor": None}
    for owner, cursor in [("u", "z"), ("nobody", None)]:
        assert api.page(owner, 2, cursor) == (200, {"items": [], "next_cursor": None})
    assert api.page("u", 1, "")[1]["items"] == [{"id": "a", "text": "A"}]
    assert api.page("u")[1]["next_cursor"] == "aa"


@pytest.mark.parametrize("limit", [0, -1, 6, True, False, "2", 2.0, None])
def test_bad_limits(limit):
    _, api = setup()
    status, body = api.page("u", limit)
    assert status == 400 and "error" in body


@pytest.mark.parametrize("cursor", [1, False, [], {}])
def test_bad_cursors(cursor):
    _, api = setup()
    status, body = api.page("u", 2, cursor)
    assert status == 400 and "error" in body


def test_client_follows_pages():
    _, api = setup()
    assert list(Client(api, "u").iter_items(1)) == Client(api, "u").items()
    assert list(Client(api, "none").iter_items()) == []
    with pytest.raises(ValueError) as exc:
        list(Client(api, "u").iter_items(0))
    assert exc.value.args == (400,)


def test_client_propagates_later_failure():
    class Stub:
        def page(self, owner, limit=2, cursor=None):
            if cursor is None:
                return 200, {"items": [{"id": "a", "text": "A"}], "next_cursor": "a"}
            return 503, {"error": "unavailable"}

    iterator = iter(Client(Stub(), "u").iter_items())
    assert next(iterator) == {"id": "a", "text": "A"}
    with pytest.raises(ValueError) as exc:
        next(iterator)
    assert exc.value.args == (503,)
