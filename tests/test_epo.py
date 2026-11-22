import httpx

from src.criteria import assess
from src.sources import epo


def binding(number, name, title, ipc="http://data.epo.org/linked-data/def/ipc/B65G1-00"):
    values = {
        "pub": f"http://data.epo.org/linked-data/data/publication/EP/{number}/B1/-",
        "number": number,
        "date": "2025-05-14",
        "name": name,
        "title": title,
        "filing": "2021-03-01",
        "ipc": ipc,
    }
    return {k: {"type": "literal", "value": v} for k, v in values.items()}


BINDINGS = [
    binding("1000001", "Testowa Fabryka Spolka z ograniczona\nodpowiedzialnoscia", "GREIFER FÜR EINE MASCHINE"),
    binding("1000001", "Testowa Fabryka Spolka z ograniczona\nodpowiedzialnoscia", "GRIPPER FOR A MACHINE"),
    binding("1000001", "Testowa Fabryka Spolka z ograniczona\nodpowiedzialnoscia", "PRÉHENSEUR POUR UNE MACHINE"),
    binding("1000002", "KOWALSKI, Jan", "METHOD OF TESTING"),
    binding("1000003", "Stalpa Stanislaw Testowy", "DEVICE FOR TESTS"),
    binding("1000004", "Politechnika Testowa", "A METHOD OF OBTAINING CEMENT", "http://data.epo.org/linked-data/def/ipc/C04B7-00"),
]


def client(status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        assert b"countryCode" in request.content
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(200, json={"results": {"bindings": BINDINGS}})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_cards_of_institutions_only():
    data = epo.load(client=client())
    cards = {c.id: c for c in data.records}
    # Natural persons and sole traders with a first name are not used.
    assert set(cards) == {"epo-1000001", "epo-1000004"}
    gripper = cards["epo-1000001"]
    assert gripper.title == "GRIPPER FOR A MACHINE"
    assert gripper.institution.name == "Testowa Fabryka Spolka z ograniczona odpowiedzialnoscia"
    assert gripper.institution.kind == "company" and gripper.institution.voivodeship is None
    assert "procesy przemysłowe, obróbka, transport" in gripper.keywords
    assert [e.label for e in gripper.timeline] == ["Zgłoszenie w EPO", "Patent europejski EP 1000001 B1"]
    assert cards["epo-1000004"].institution.kind == "university"
    for card in cards.values():
        assert card.novelty.value == 4 and card.sources[0].license.startswith("CC BY 4.0")
        assert card.assessment.model_dump() == assess(card.model_dump())


def test_failed_endpoint_gives_an_error():
    data = epo.load(client=client(status=503))
    assert data.records == [] and data.errors
