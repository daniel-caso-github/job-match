from src.domain.services.id_hasher import make_id


def test_make_id_is_deterministic():
    a = make_id("himalayas", "https://x/y")
    b = make_id("himalayas", "https://x/y")
    c = make_id("remotive", "https://x/y")
    assert a == b
    assert a != c
    assert len(a) == 16
