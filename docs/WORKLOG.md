# Work log

Add an entry after each step of work. Give the date, the person and the changes. The newest entry is at the top.

## 2026-11-22, MikolajRowicki (branch 44-analytics)

- Add anonymous usage counters (FAQ, section 7): table `usage` (day, kind, value, count) in `src/db.py`.
- `/api/search` counts the filters (area, group, voivodeship) and "z frazą" or "bez frazy". It never stores the text of a query, because the text can contain a name.
- `/api/innovations/{id}` counts the viewed card and its area.
- Add `GET /api/stats?days=30`: the top values of each counter, with the titles of the viewed cards.
- No IP address, no user identifier, no cookie. Add a test that the text of a query is not stored.

## 2026-11-22, MikolajRowicki (branch 42-submission, issue #19)

- Add `LICENSE` with the text of EUPL-1.2 (SPDX). The rules of the task (§1 point 10, §4) require this licence; the file did not exist.
- Add `docs/screenshots/` with 5 screenshots of the real data (search, administrative card, technological card, comparison, "O radarze") and the section "Zrzuty ekranu" in `README.md`.
- Checks: no trace of AI tools in the files and in the commit messages; no secrets; no large data files in git; 116 tests and 3 slow tests pass.
- BZP: the words of the patent law ("wzór użytkowy", "prawo ochronne") are generic now. Before, a utility model matched a purchase of heat because of "własność, użytkowy".
- NCBR: a line break in the list of beneficiaries separates two beneficiaries. Before, a consortium became one long name.

## 2026-11-22, MikolajRowicki (branch 40-more-sources, more sources)

- Add `src/sources/epo.py`: European patents (B1) of applicants with an address in Poland, last 5 years, from the EPO Linked Open Data SPARQL endpoint (CC BY 4.0, no key, `robots.txt` allows `/linked-data/query`). 1164 cards in 13 s.
  - The data has no city, so the card has no voivodeship. The title is the English one; the keywords come from the IPC section in Polish.
  - Only clear institutions: a legal form of a company, a university or an institution word. Natural persons ("KOWALSKI, Jan") and sole traders with a first name ("Stalpa Stanislaw ...", often without Polish letters) go out.
  - Implementation level 2 and TRL 4 as estimates, as for the RAD-on patents; novelty 4 (a European patent).
- Not used: Erasmus+ project results (HTTP 403 for automatic requests).
- Add `tests/test_epo.py`.

## 2026-11-22, MikolajRowicki (branch 38-review-fixes, review against the criteria of the jury)

- The review compared `README.md`, the presentation and the code. Fixes:
  - Add `GET /api/export.csv` (UTF-8 with BOM, separator `;`): the presentation (slide 9) and the README promised a CSV export, but it did not exist.
  - Add `search.group_bonus()`: the cards that meet the condition of the user group get +0.1 in the order. The README table of the user groups now describes the real rules. `rank_score` of the contract does not change.
  - `PageFetcher` deletes cached pages older than 7 days (TDM: copies only as long as necessary).
  - README: no claim of a hybrid search with embeddings (the search is BM25 on lemmas); no claim of a general crawler; the card section "Gdzie można zastosować"; the CSV export and `/api/criteria`; new limits (no voivodeship in national lists, noise in BZP matches, Kohesio licence); the development list without the sources that exist now.
- Add tests: CSV export, group bonus, deletion of old cached pages.

## 2026-11-22, MikolajRowicki (branch 36-kohesio, new source)

- Add `src/sources/kohesio.py`: finished EU projects of 2014-2020 in Poland from the Kohesio API (no key, no documentation).
  - Search: 5 Polish phrases, 50 projects each. Details: `/api/projects/project?id=...` through `PageFetcher` (cache, pause).
  - Only finished projects. The mapping uses `fe_projects.row_to_innovation()`; the area uses the categories of 2014-2020 (078-080 e-administration, 049-052 and 115-118 education).
  - The voivodeship comes from the name of the regional programme. National programmes have no voivodeship.
  - Licence: none stated; the card writes the reuse policy of the Commission (Decision 2011/833/EU) as an assumption.
- Not used: CORDIS. `robots.txt` of cordis.europa.eu forbids `/data/`, the folder of the bulk files.
- Kohesio uses the innovation filter of the FE list (or the categories 078-080): construction or equipment only goes out. Result: 56 cards (12 in Podkarpackie, the others national).
- `pipeline.store()` now deletes the records of a source that the source does not give any more. If the source gives no records (an error), the old records stay.
- Add `tests/test_kohesio.py`.

## 2026-11-22, MikolajRowicki (branch 34-ncbr, new sources)

- Add `src/sources/ncbr.py`: the NCBR list "Wyszukiwarka sukcesów beneficjentów" (316 projects) and the page of each project. The card takes only the sections about the problem and the users. 312 cards, all of Poland (178 technological, 103 educational).
  - Beneficiaries that are natural persons (also "Firma Jan Kowalski") are not used. Sentences with "dr", "prof." and a name are removed from the description.
  - The page has typing errors in the voivodeships ("zachodnioporskie"); `difflib` maps them to the official names.
  - The list is small and national, so the loader ignores the voivodeship filter.
- Add `src/sources/interreg.py`: Interreg 2021-2027 projects (dane.gov.pl, dataset 15971, CC0 1.0). It uses `fe_projects.row_to_innovation()`. A project is kept if the FE filter keeps it or if the text describes a solution (system, platform, method, technology). 101 cards.
- Move the page fetcher (cache, `robots.txt`, Crawl-delay) from `competitions.py` to `src/sources/__init__.py` (`PageFetcher`), so that all web loaders use it.
- `fe_projects.person_name()` has a new parameter `foreign`. Only Interreg uses it: names of foreign institutions ("Obec Skalité", "Cardinal Stefan Wyszynski Hospital") are not persons. The FE list keeps the old rule, so "Jan Kowalski Auto Center" stays hidden.
- Add `tests/test_ncbr.py`, `tests/test_interreg.py` and the fixtures `ncbr_list.html`, `ncbr_detail.html` (made-up persons only).

## 2026-11-22, MikolajRowicki (branch 32-link-records, issue #13)

- Add the step `link_records()` to `src/pipeline.py`. It runs after each update and joins records of different sources about the same innovation.
- Rule: the same institution (name without words such as "gmina" or "sp. z o.o.") and a Jaccard index of the title lemmas of 0.33 or more. At 0.9 or more, the records are one project: one card with both sources.
- A linked card gets the sources and the timeline events of the other record. Two sources raise K5 (credibility) to 4 ("Dwa niezależne źródła") as a fact; then the assessment is calculated again.
- The step reads all records in the order of the id, so the result does not depend on the order of the updates. A second run changes nothing.
- Result on Podkarpackie: 2 merged duplicates (RAD-on project = FE project) and 4 pairs "grant -> patent", for example "Elektroda nasadkowa do zgrzewania oporowego": grant 2017, application 2022, patent 2025.
- Add `db.delete_innovation()`, `db.all_innovations()` and `tests/test_linking.py`.
- Issue #13 is complete.

## 2026-11-22, MikolajRowicki (branch 28-competitions, issue #10)

- Add `src/sources/competitions.py`: one card for each awarded or distinguished project of the competition "Innowacyjny Samorząd" (Serwis Samorządowy PAP, pages on wartowiedziec.pl).
- The result pages are in `data/web_sources.csv`, category `competition_results` (S044: VII edition 2026, S045: IV edition 2023). The column `strategy` names the parser.
- The loader obeys `robots.txt` and its Crawl-delay (60 s on wartowiedziec.pl). It keeps the pages in `data/cache/pages/` for 7 days.
- The parser finds "X za projekt „Y”", lists "I miejsce: X (Y)" and titles with the name of the JST. It changes the case of the name ("powiatowi krotoszyńskiemu" -> "Powiat krotoszyński"). It skips sentences with quotes of persons.
- The date comes from the page (`class="date"`), because the date of trafilatura is not correct for this site.
- Implementation level 5 and credibility 5 are facts: the page says that the competition awards implemented projects. The card gets an "award" event.
- Result: 46 cards (VII edition: 16 prizes and 22 distinctions; IV edition: 8 prizes). Only some cards have a voivodeship: the pages do not give it.
- Not used: "Kierunek innowacja" (only names of teachers, no description), PARP "Polski Produkt Przyszłości" (bot protection), VI edition 2025 (free text without quotes).
- Add `tests/test_competitions.py` and `tests/fixtures/competition_page.html` (short quotes only, a made-up person name for the test).

## 2026-11-22, MaciejMomot (branch 27-ui-polish)

Changes after the review of the user interface by the team.

- New look with the colors of PCI (logo: blue #0085cc, green #6bb437). A header with the menu "Szukaj, Porównanie, O radarze". No footer.
- The search is in a blue hero band. Each result shows the potential as a ring on the right.
- Pagination: the button "Pokaż więcej" and the text "Znaleziono N. Pokazano M." `GET /api/search` has the new parameter `offset`. `src/search.py` reads up to 2000 candidates (`MAX_CANDIDATES`); an empty query takes 0.4 s.
- Labels: "szacunek" became "przybliżone" and "fakt" became "ze źródła", because users read "szacunek" as "respect". The reason, the quote and the link open under "dlaczego?" or "cytat". `AGENTS.md`, rule 5, now tells the same labels.
- The card: tiles for the main facts, a side panel with the score, the range and the confidence, and the criteria as bars. "Jak liczymy ocenę?" is short and has no version of the criteria.
- New page `web/about.html` ("O radarze"): the status of the sources, the meaning of the labels, the method with the criteria, the weights, the scales, the references and the version, and the privacy. The search page shows only a warning if a source failed.
- No text tells that the source of the criteria is the FAQ: the references in `src/criteria.py` and the text in `README.md` changed.
- `src/sources/fe_projects.py`: the type keeps the case ("projekt FE: rozwiązania TIK…"). `src/applications.py`: names of the missing criteria, not codes.

## 2026-11-22, MikolajRowicki (branch 26-bzp, issue #13)

- Add `src/sources/bzp.py`: contract notices of the last 180 days from the e-Zamówienia API (no key) for 7 CPV groups. One request for each group; a full page (500) splits the date window. One request each 3 s.
- The loader stores the buyer, the subject, the CPV codes, the date and the link. It does not store contractors (a contractor can be a natural person).
- Findings: the parameter `PageNumber` has no effect; `CpvCode` filters; `organizationProvince` uses TERYT codes (PL18 = podkarpackie). No block in 7 requests with a pause of 3 s.
- Add the tables `notices` and `notices_fts` to `src/db.py`. `python -m src.pipeline update` loads the notices after the sources (`--source bzp` loads only them). Podkarpackie update: 2803 notices in 152 s.
- Add `search.demand()`: the card gets the notices with a similar subject. Score: sum of the IDF weights of the common words (not generic), threshold 12. Duplicates (same buyer and subject) are removed. `DemandSignal` has new optional fields `voivodeship` and `reason` (the common words).
- The card shows the common words with the label "szacunek" (`web/app.js`).
- Check: "e-usługi w urzędzie" gives e-service purchases of Biłgoraj, Wadowice and Dąbrowa Tarnowska; school labs give purchases of school labs. Patents get few matches. Some matches are noise; the card shows the words, so the user can judge.
- Not done (part of issue #13): a timeline that joins records of different sources, and K5 from independent events.
- Add `tests/test_bzp.py` and `tests/fixtures/bzp_notices.json` (5 recorded notices without the HTML body and without contractors).

## 2026-11-22, MikolajRowicki (branch 24-use-cases, issue #15)

- Add `src/applications.py` (rules v0.1): where an innovation can be used and by whom (task section 6, points d and e). The card gets `applications`:
  - sectors with typical recipients, with a quote from the source;
  - user groups of the FAQ with the reason;
  - other institutions with similar innovations (candidate partners or next adopters);
  - the path with its reason, the measures of effectiveness and the reference: P1 technology transfer, P2 market use, P3 replication in another institution, P4 pilot with evaluation, P5 more data.
- Add the models `Applications`, `Sector`, `Audience`, `Adopter` and `Path` to `src/models.py`. `search.detail()` fills `applications`.
- Add the section "Gdzie można zastosować i kto może wdrożyć" to the card (`web/app.js`, `web/style.css`).
- RAD-on: skip projects without a signal of a solution in the text (for example dictionaries and history). Podkarpackie now gives 927 records.
- Add `tests/cases.json` (7 cases: 3 areas, 3 sources, 2 voivodeships; 2 demo cases) and `tests/test_cases.py`.
- Add `pytest.ini`: the marker `slow`. `pytest` skips the slow tests; `pytest -m slow` runs them with the network.
- Check: 98 tests pass. The slow tests pass: technological demo (RAD-on, 32 s), administrative demo (FE, 12 s), new card in 30 s or less.
- Add the demo procedure to `README.md`.

## 2026-11-22, MaciejMomot (branch 25-fe-projects, issue #7)

- Add `src/sources/fe_projects.py`: the loader of the list of FE 2021-2027 projects (dane.gov.pl, dataset 13939, CC0 1.0). Register it in `src/pipeline.py` as `fe`.
- The loader asks the API for the newest XLSX of the dataset and downloads it once to `data/cache/`. If the API fails, it uses a file in `data/cache/` that a person downloaded.
- Filter: a category of intervention of research, innovation or ICT, or an innovation word in the title, and a description of 80 characters or more. Result for Podkarpackie: 779 of 2352 projects (with 144 projects for the whole country).
- Area by rules: education categories or words, then public bodies and e-services, then technological.
- The descriptions come from the applications (future tense). Thus the implementation level comes from the dates: ended 4, running 2, not started 1. The keyword rules gave wrong levels on this text.
- Personal data: a beneficiary name with a first name and a surname (a natural person or a sole trader) is replaced with "dane ukryte". The loader also removes the name from the title and the description.
- Move the summary function of RAD-on to `src/sources/__init__.py` (`summary_quote`). Both loaders use it.
- Add `tests/test_fe_projects.py` and `tests/fixtures/fe_projects.json`: 7 real public rows and 1 synthetic sole trader (not a real person).
- Check: "e-usługi w urzędzie" finds the e-office projects of gminas in Podkarpackie (use case 2 of the demo).

## 2026-11-22, MaciejMomot (branch 23-level-rules)

- Make the keyword rules of `estimate_implementation_level()` stricter. With the real RAD-on data (Podkarpackie), 20 projects got level 5, and most of them were wrong.
- Level 5 needs a statement about use: "jest stosowany", "wdrożono", "funkcjonuje od", "stosowane w praktyce". A single word ("funkcjonującym", "stosowaną") does not count.
- A negation ("nie były stosowane", "nie wdrożono") gives no level.
- A plan covers the rest of the clause: "zostanie opracowana i wdrożona", "wdrożona zostanie", "ma na celu", "przewidziane jest", "zaplanowane".
- Result on the same data: level 5 has 2 records (was 20), level 4 has 9 (was 12).
- Add 15 test cases, most of them from the RAD-on texts.

## 2026-11-22, MaciejMomot (branch 21-connect-api, issue #12)

- Connect the web page to the API of PR #34. Remove the sample data fallback from the search, the card and the comparison. The tests still use `web/sample/`.
- Add the panel "Źródła danych" to the search page: the number of records and the date of the last check of each source (`GET /api/sources`).
- If a source failed at the last update, the page shows a warning with the name of the source. If the database is empty, the page tells it.
- The card tells the user when an id is not in the database (404).
- Fix the "0" on the card of a record without keywords (found by MikolajRowicki in PR #34).
- Check: headless Edge on the uvicorn server with the real database (Podkarpackie, 977 records): filters, card, 404, comparison, a failed source, an empty database, no console errors.

## 2026-11-22, MikolajRowicki (branch 20-pipeline-api, issues #9 and #11)

- Add `src/pipeline.py`: `python -m src.pipeline update [--voivodeship X] [--source Y]`. It loads each source, writes the records and the full-text index and records the status of each source. A failed source does not stop the update.
- Add `src/search.py`: SQLite FTS5 search on Polish lemmas (simplemma) with a prefix match, filters (area, voivodeship, minimum implementation level), the user group as a sort preference, and similar innovations (same words in the title and the keywords).
- Ranking: `rank_score = 0.7 × relevance + 0.3 × potential / 100`. Relevance is BM25 divided by the best BM25 of the query.
- Add to `src/app.py`: `GET /api/search`, `GET /api/innovations/{id}` (with `similar`) and `GET /api/sources`. The variable `RADAR_DB` changes the path of the database.
- Add `tests/test_pipeline.py` (recorded RAD-on responses, no network).
- Add the update step to the start procedure in `README.md`.
- Check: Podkarpackie, 977 records. A search takes 0.01-0.07 s. Headless Edge shows the search page and the card with the real data.
- Open items:
  - Similar innovations use common words only. Embeddings come later. An example: a patent about collectors of a helicopter finds solar collectors.
  - The card shows "0" under "Gotowość technologiczna" if the record has no keywords (`web/app.js`, line 659: `item.keywords?.length && ...`).

## 2026-11-22, MikolajRowicki (branch 14-radon-loader, issue #8)

- Add `src/sources/__init__.py`: `SourceData` holds the records of one source and the metadata (source, date of the data, date of the download, license, errors).
- Add `src/sources/radon.py`: the loader of RAD-on (`institutions`, `products`, `projects`). The function `load(voivodeships)` returns cards (`Innovation`) with an assessment. `None` means all of Poland.
- The loader takes the city and the voivodeship from the RAD-on list of institutions. Thus the code has no list of institutions.
- The loader does not read the data of persons (inventors, project managers).
- Patent: technological area, implementation level 2 and TRL 4 as estimates, novelty 3 (protection in Poland) or 4 (abroad), credibility 3 as a fact.
- Project: the keyword rules of `src/criteria.py` give the level and the novelty. A finished project without keywords gets level 2. Projects of NCN, NAWA and Fulbright only are skipped: basic research and mobility are not innovations (Oslo Manual).
- If one request fails, the loader records the error and continues.
- Add `tests/test_radon.py` and `tests/fixtures/radon_responses.json` (recorded responses without personal data).
- Check: Podkarpackie gives 977 records (802 patents and utility models, 175 projects) in 30 s without errors. Command: `python -m src.sources.radon --voivodeship podkarpackie`.

## 2026-11-22, MaciejMomot (branch 17-presentation, issue #17)

- Add the first version of the presentation: `docs/presentation/Radar_innowacji.pptx` and `Radar_innowacji.pdf` (10 slides, Polish, speaker notes).
- Add `docs/presentation/build_deck.js`. It builds the deck from the screenshots in `docs/presentation/img/`. The tools (PptxGenJS, sharp, react-icons) are not dependencies of the application. The procedure is in the head of the script.
- The screenshots show the sample data of PR #24. Make them again when the API and the real data exist.
- Record the licenses of the presentation tools and of the Font Awesome icons (CC BY 4.0) in `README.md`.
- Correct the times of my earlier entries in this file. They now agree with the git history.

## 2026-11-22, MaciejMomot (branch 15-compare, issue #28)

- Add the comparison of 2-4 innovations: `web/compare.html` and the code in `web/app.js` and `web/style.css`.
- A checkbox "Porównaj" on each result and on the card. A bar at the bottom shows "Do porównania: N z 4" and the link to the comparison.
- The table has the innovations in columns. The rows are the basic data, the potential, K1-K5 with the weights, the sources, the demand signals and the timeline.
- Each value shows "fakt" or "szacunek". The highest potential has the tag "najwyższy". The table hides the potential of an innovation without sources.
- The selection stays in `localStorage` (key `radar.compare.v1`) and in the URL (`compare.html?ids=...`). Thus a user can send the link.
- Without the API, the page uses the sample data. Only one sample record has the full assessment, so other columns show "brak oceny".
- Check: headless Edge on the uvicorn server with the sample data (limit of 4, card button, remove, phone width, no console errors).

## 2026-11-22, MaciejMomot (branch 13-trl-missing)

- Accept the contract changes of PR #24. Change the TRL rule to the contract: `trl: null` means "nie dotyczy", and `trl.value: null` means that the data is missing.
- `src/criteria.py`: K2 does not apply only if the field `trl` is null. A missing TRL value now widens the range, as the other criteria do.
- `web/app.js`: the card shows "nie dotyczy" only for `trl: null`. For a null `trl.value`, it shows "brak danych".
- Add a test for a missing TRL value. No sample record has a null `trl.value`, so the sample assessments do not change.

## 2026-11-22, MaciejMomot (branch 11-watchlists, issue #14)

- Add watchlists to the search page: the button "Obserwuj to wyszukiwanie" saves the query and the filters.
- The saved queries stay only in the browser (`localStorage`, key `radar.watchlists.v1`). No login and no personal data.
- The panel "Obserwowane wyszukiwania" shows the number of new results of each saved query since the last visit.
- A new result has the tag "Nowe od ostatniej wizyty". After the visit, the page records the results as seen.
- The watchlists use the same search function as the page. Thus they operate with the API and with the sample data.
- Check: headless Edge with the sample data of PR #24 (save, simulated update, new tags, reset after the visit, remove).

## 2026-11-22, MikolajRowicki (branch 06-record-schema, issue #3)

- Add `src/models.py`: the record schema (`Innovation`, `FieldValue`), the API responses and the Polish labels of all codes (`LABELS`).
- Add `src/db.py`: SQLite schema with the tables `innovations` (JSON and filter columns), `innovations_fts` (FTS5), `innovations_vec` (sqlite-vec, cosine, 768 dimensions) and `sources`.
- Add `tests/fixtures/sample_innovations.json`: 18 real records from RAD-on, NCBR, wartowiedziec.pl and polishscience.pl. The set has all three areas and 9 voivodeships. The records have no names of persons.
- Add `web/sample/search.json` and `web/sample/innovation.json` for the web page.
- Add `tests/test_models.py`. The test checks that each quote is a part of the source text. It also checks that `src.criteria.assess()` gives the same assessment again.
- Changes to the contract of the issue (Maciej must accept them):
  - full `FieldValue` in the search results;
  - `trl: null` means "not applicable", and `trl.value: null` means "no data";
  - `Assessment` has the output of `src/criteria.py` (`score`, `points`, `applicable`, `fact_share`, `missing`).
- Merge with `main`: remove the planned `GET /api/meta`, because `GET /api/criteria` (Maciej) gives the criteria. The web page keeps its copy of the labels. `LABELS` in `src/models.py` is for the backend.
- Calculate the assessment of the sample records again with `src.criteria.assess()`.
- Findings:
  - The BZP API blocked the second request ("Dostęp zablokowany"). Issue #13 must use a low request rate and a cache.
  - The publication dates from trafilatura are not correct for gov.pl and wartowiedziec.pl. Thus `data_date` stays empty.
  - No sample record has the confidence "high", because most criteria are estimates.
  - Page text contains non-breaking spaces. The pipeline must normalize them before the quote check.
- A script outside the repository made the sample records.

## 2026-11-22, MaciejMomot (branch 09-card-page, issue #6)

- Add the card page `web/innovation.html`. The code is in `web/app.js` and `web/style.css`.
- Sections: title and summary, main facts, assessment, sources, signal timeline, demand signals (BZP), description, similar innovations.
- Each field shows "fakt" (quote and source link) or "szacunek" (reason). A null TRL shows "nie dotyczy".
- The assessment table joins each criterion to the field that caused it. "Jak liczymy ocenę?" shows the scales, weights and references.
- The card shows no assessment if the innovation has no sources (`AGENTS.md`, rule 1).
- Add `GET /api/criteria` in `src/app.py`. It returns `CRITERIA` from `src/criteria.py`, so the web page has no copy of the criteria.
- The page calls `GET /api/innovations/{id}`. If the API does not exist yet (`/api/sources` gives 404), the page uses `web/sample/innovation.json`.
- Links from the data use only http and https.
- Check: headless Edge with a test card (desktop and phone width, no console errors).

## 2026-11-22, MaciejMomot (branch 07-search-page, issue #5)

- Make the search page: `web/index.html`, `web/app.js`, `web/style.css`. Plain HTML and JS, no library, no build step.
- Add `web/config.json`: the default voivodeship and the search examples. Thus the code has no region.
- The page calls `GET /api/search`. If the API gives 404, the page uses `web/sample/search.json` (issue #3), filters it in the browser and shows a notice.
- The first view shows the default voivodeship. A search with a phrase covers all of Poland, if the user did not select a voivodeship.
- The page accepts a FieldValue or a plain value in each field. A tag with an estimate shows "szacunek" and the reason.
- The page builds the DOM with `textContent` only. Thus text from the sources cannot inject HTML.
- Check: headless Edge with test data (default view, search, filter, back button, no console errors).

## 2026-11-22, MaciejMomot (branch 05-readme, issue #16)

- Write the structure and the first full text of `README.md` in Polish: problem, solution, process, main functions, user groups, data sources, criteria and rules, assumptions and limits, scale-up, security, integration, development, license.
- Keep the start procedure and the license table of MikolajRowicki.
- Open items: MikolajRowicki checks the data sources part. Before the submission, check that each function in the README operates (comparison, CSV export, watchlists).

## 2026-11-22, MikolajRowicki (branch 04-app-skeleton, issue #2)

- Add the application skeleton: `src/app.py` (FastAPI, `GET /api/health`, static files from `web/`), `web/index.html`, `tests/test_app.py`.
- Add `requirements.in`, `requirements-dev.in` and the lock `requirements.txt`. PyTorch and sentence-transformers come later with the search (issue #9).
- Decisions: the web page is static HTML and JS that calls the JSON API (no Jinja2). The start command is `uv run --no-project uvicorn src.app:app --reload`.
- Check: sqlite-vec 0.1.9 and FTS5 load on Python 3.13 (Windows). All licenses are permissive, except certifi (MPL-2.0, a transitive dependency of httpx, used without change).
- Add `README.md` with the start procedure and the license table.

## 2026-11-22, MaciejMomot (branch 03-criteria-module, issue #4)

- Add `src/criteria.py`: the criteria K1-K5 with Polish names, scales, weights and references (`CRITERIA`), and the function `assess()`.
- `assess()` gives `potential`, `low`, `high`, `confidence`, `fact_share`, `criteria_version`, `criteria` and `missing`.
- Decisions:
  - A TRL value of null means "nie dotyczy". The weight of K2 then goes to the other criteria in proportion.
  - An unknown value of another criterion gives a range: 0 for `low`, 5 for `high`.
  - `potential` uses only the known criteria. Thus it is always in the range. If no criterion is known, `potential` is null.
  - Each entry of `criteria` has `value`, `score` (0-5), `weight` (after the change of weights), `points`, `kind` and `applicable`. This adds fields to the contract of issue #3.
- Add `estimate_implementation_level(text)` and `estimate_novelty(text)`: rules with Polish keywords, without AI. A plan ("zostanie wdrożony") counts as a concept. The evidence is always an exact part of the text.
- Add `tests/test_criteria.py` (41 tests).

## 2026-11-22, MikolajRowicki (branch 02-web-sources)

- Change the second team member in `AGENTS.md` to `MaciejMomot` (odd numbers).
- Deadline of the project: 2026-11-22 10:00.

## 2026-11-22, MikolajRowicki (branch 02-web-sources)

- Record decisions in `docs/project.md`: all user groups of the FAQ, main flow (phrase, recommendations, card), all of Poland with Podkarpackie first, summaries without a language model at the start, source of the weights.

## 2026-11-22, MikolajRowicki (branch 02-web-sources)

- Research how venture capital funds find projects. Add to `docs/project.md`: signal timeline, watchlists and alerts, arguments for the pitch (PFR Starter Science, EQT Motherbrain), hit rate and coverage.

## 2026-11-22, MikolajRowicki (branch 02-web-sources)

- Add `data/web_sources.csv`: 43 web sources in 8 categories, with the HTTP check and the crawl strategy of each category.
- Test the crawler on the 35 sources that answered. Competitions and gov.pl aggregators give the best results. Home pages of media give noise. Record the result in `docs/project.md`, section 6.1.

## 2026-11-21, MikolajRowicki (branch 02-web-sources)

- Test the crawler on 29 sites of JST and universities in Podkarpackie (script outside the repository). Result: 52 candidates, about 7 real innovations. Record the result and the next changes in `docs/project.md`, section 6.1.

## 2026-11-21, MikolajRowicki (branch 02-web-sources)

- Add the crawler of institution web pages to `docs/project.md` as source 2 (section 6.1).
- Add the list of sources not to use: LinkedIn and Facebook, with the reasons.
- Add EPO OPS and UPRP API as later sources, if the team makes accounts.

## 2026-11-21, MikolajRowicki

- Add `docs/project.md`: the concept from the FAQ, the innovation card, the five criteria (v0.1), the data sources, the architecture, the demo and the open decisions.

## 2026-11-21, MikolajRowicki

- Read the new file `task/Radar Innowacji FAQ.pdf`. The FAQ changes the scope: discovery and assessment of existing innovations, not a platform for submissions or investors.
- Change `AGENTS.md` for the FAQ: project description, three areas, Oslo Manual definition, FAQ criteria, innovation card, facts versus estimates, user groups, regular updates.
- Remove the rules about creator data, minors and the label for AI text.

## 2026-11-21, MikolajRowicki

- Finish the final report `docs/reports/Innovation radar landscape.md`. It has the existing solutions, the data sources, the rubric draft v0.1, the stack, the legal checklist and a 15-hour plan.
- Add rules from the research to `AGENTS.md`: licenses of model weights, forbidden components, hidden personal data, AI Act rules.
- Next step: the team selects the concept and writes `docs/project.md`.

## 2026-11-21, MikolajRowicki

- Finish the research on the 3 stopped topics. All 7 notes are in `docs/research_notes/Innovation radar landscape/`:
  - `data_patents_science.md`
  - `data_public_projects.md`
  - `tech_methods_stack.md`
- Start the final report `docs/reports/Innovation radar landscape.md`.

## 2026-11-21, MikolajRowicki

- Finish 4 of 7 research notes in `docs/research_notes/Innovation radar landscape/`:
  - `poland_landscape.md`
  - `eu_global_landscape.md`
  - `assessment_frameworks.md`
  - `problem_gaps_legal.md`
- Stop the research on 3 topics before the end: patent and science data, public project data, NLP methods and stack. Do this research again.
- The final report `docs/reports/Innovation radar landscape.md` does not exist yet.

## 2026-11-21, MikolajRowicki

- Change `AGENTS.md` from the KOWR task to the PCI task "Radar innowacji". New sections: personal data and security, rules of the process, criteria of the jury. The license of the solution is EUPL-1.2.
- Change `KAGGLE.md` for this project: Python 3.13, clone of the private repository with a GitHub token, examples for embeddings and language models.
- Add `.gitignore`.
- Start the research about existing solutions, data sources, assessment criteria, methods and law. Notes go to `docs/research_notes/Innovation radar landscape/`. The report goes to `docs/reports/Innovation radar landscape.md`.
