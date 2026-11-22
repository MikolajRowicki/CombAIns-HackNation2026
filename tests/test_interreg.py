from datetime import date

import openpyxl

from src.criteria import assess
from src.sources import interreg

HEADER = [
    "Program / Programme", "Numer projektu / Project no.", "Tytul projektu / Project title",
    "Opis projektu / Project description", "Data rozpoczęcia realizacji / Project start date",
    "Data zakończenia realizacji / Project end date", "Wydatki 0gółem (EUR) / Total costs (EUR)",
    "Stopa dofinansowania", "Fundusz / Fund", "Cel szczegółowy", "Nazwa partnera wiodącego/ Lead partner name",
    "Kod pocztowy", "Kraj / Country", "Województwo lub region / Voivodeship or region ", "Powiat / Poviat",
    "Gmina / Commune", "Miejscowość / City", "Nazwa partnera wiodącego i partnerów / Lead partner and partners",
    "Zakres interwencji / Intevention field",
]
DESCRIPTION = "Projekt wdroży wspólny system wczesnego ostrzegania przed powodzią dla gmin po obu stronach granicy."


def row(title, lead, country, voivodeship, category="059 Działania w zakresie przystosowania się do zmian klimatu"):
    return [
        "Program Interreg Polska-Słowacja 2021-2027 / Interreg", f"PLSK.01.01-IP.01-{abs(hash(title)) % 9999:04d}/23",
        title, DESCRIPTION, "2023-06-01", "2025-05-31", 700000, 80, "EFRR", "CP2", lead, "32-650", country,
        voivodeship, "krośnieński", "Dukla", "Dukla", f"{lead} | Obec Partnerska", category,
    ]


def test_load_from_a_cached_file(tmp_path, monkeypatch):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["Interreg 2021-27"])
    sheet.append([])
    sheet.append(HEADER)
    sheet.append(row("Wspólny system ostrzegania przed powodzią", "Gmina Dukla", "Polska", "PODKARPACKIE"))
    sheet.append(row("Platforma współpracy ratowników", "Obec Skalité", "Słowacja", "Žilinský kraj"))
    sheet.append(row("Festyn pogranicza", "Jan Kowalski", "Polska", "PODKARPACKIE", "165 Turystyka"))
    book.save(tmp_path / "interreg_1.xlsx")
    monkeypatch.setattr(interreg, "CACHE", tmp_path)

    def broken(client):
        raise ValueError("API does not answer")

    monkeypatch.setattr(interreg, "_resource", broken)
    data = interreg.load(["podkarpackie"])
    assert any("API" in e for e in data.errors)
    cards = {c.title: c for c in data.records}
    # The festival has the same description, so it passes the filter; its lead partner is a person: hidden.
    assert cards["Wspólny system ostrzegania przed powodzią"].institution.voivodeship == "podkarpackie"
    assert cards["Platforma współpracy ratowników"].institution.name == "Obec Skalité"
    assert cards["Platforma współpracy ratowników"].institution.voivodeship is None
    assert "Kowalski" not in cards["Festyn pogranicza"].model_dump_json()
    for card in cards.values():
        assert card.id.startswith("interreg-")
        assert card.sources[0].name == interreg.NAME and card.sources[0].license == "CC0 1.0"
        assert card.assessment.model_dump() == assess(card.model_dump())
    assert cards["Wspólny system ostrzegania przed powodzią"].timeline[0].date == date(2023, 6, 1)
