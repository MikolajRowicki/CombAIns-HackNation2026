# Radar innowacji

Narzędzie do odkrywania i oceny istniejących polskich innowacji z obszaru technologicznego, edukacyjnego i administracyjnego. Projekt powstaje w ramach zadania Podkarpackiego Centrum Innowacji na HackNation 2026.

> Ten plik jest w budowie. Pełny opis (źródła danych, kryteria oceny, skalowanie, bezpieczeństwo, integracje, rozwój) zostanie uzupełniony.

## Uruchomienie

Wymagania: [uv](https://docs.astral.sh/uv/getting-started/installation/).

W katalogu głównym repozytorium:

```bash
uv venv --python 3.13 .venv
uv pip sync --python .venv requirements.txt
uv run --no-project uvicorn src.app:app --reload
```

Aplikacja działa pod adresem http://127.0.0.1:8000.

Testy:

```bash
uv run --no-project python -m pytest
```

## Źródła danych

Dane przykładowe (`tests/fixtures/sample_innovations.json`, 18 rekordów) pochodzą z publicznych źródeł, pobranych 22.11.2026. Nie zawierają danych osobowych: aplikacja pomija nazwiska wynalazców i autorów.

| Źródło | Zawartość | Licencja i sposób użycia |
|---|---|---|
| [RAD-on (OPI PIB)](https://radon.nauka.gov.pl/opendata/polon/products), API `products` | patenty uczelni | CC0 1.0 |
| [NCBR: Wyszukiwarka sukcesów beneficjentów](https://www.gov.pl/web/ncbr/wyszukiwarka-sukcesow-beneficjentow) | opisy zrealizowanych projektów | licencja nie jest podana; zapisujemy krótkie cytaty i link |
| [wartowiedziec.pl](https://wartowiedziec.pl) | laureaci konkursu „Innowacyjny Samorząd”, usługa „Mobilny Urzędnik” | prawa wydawcy; zapisujemy krótkie cytaty i link |
| [polishscience.pl](https://www.polishscience.pl) | projekt RoboLAB | prawa wydawcy; zapisujemy krótkie cytaty i link |

## Licencje komponentów

Rozwiązanie jest przygotowane do publikacji na licencji EUPL-1.2. Wszystkie komponenty mają licencje zgodne z EUPL-1.2.

| Komponent | Zastosowanie | Licencja |
|---|---|---|
| FastAPI, Starlette | serwer aplikacji i API | MIT, BSD-3-Clause |
| Uvicorn | serwer HTTP | BSD-3-Clause |
| httpx | zapytania do źródeł danych | BSD-3-Clause |
| Pydantic | schemat danych | MIT |
| openpyxl | odczyt plików XLSX | MIT |
| Beautiful Soup | analiza HTML | MIT |
| trafilatura | wyodrębnianie tekstu ze stron WWW | Apache-2.0 |
| Protego | obsługa `robots.txt` | BSD-3-Clause |
| SQLite (FTS5), sqlite-vec | baza danych i wyszukiwanie | domena publiczna, MIT / Apache-2.0 |
| simplemma | lematyzacja tekstu polskiego | MIT |
| certifi (zależność pośrednia httpx) | certyfikaty TLS | MPL-2.0 (używana bez zmian) |
| pytest, Ruff (tylko dla deweloperów) | testy i kontrola kodu | MIT |

Pełna lista pakietów z wersjami: `requirements.txt`.
