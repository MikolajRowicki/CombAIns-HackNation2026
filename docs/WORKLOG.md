# Work log

Add an entry after each step of work. Give the date, the time, the person and the changes. The newest entry is at the top.

## 2026-11-22 01:42, MaciejMomot (branch 17-presentation, issue #17)

- Add the first version of the presentation: `docs/presentation/Radar_innowacji.pptx` and `Radar_innowacji.pdf` (10 slides, Polish, speaker notes).
- Add `docs/presentation/build_deck.js`. It builds the deck from the screenshots in `docs/presentation/img/`. The tools (PptxGenJS, sharp, react-icons) are not dependencies of the application. The procedure is in the head of the script.
- The screenshots show the sample data of PR #24. Make them again when the API and the real data exist.
- Record the licenses of the presentation tools and of the Font Awesome icons (CC BY 4.0) in `README.md`.
- Correct the times of my earlier entries in this file. They now agree with the git history.

## 2026-11-22 01:34, MaciejMomot (branch 15-compare, issue #28)

- Add the comparison of 2-4 innovations: `web/compare.html` and the code in `web/app.js` and `web/style.css`.
- A checkbox "Porównaj" on each result and on the card. A bar at the bottom shows "Do porównania: N z 4" and the link to the comparison.
- The table has the innovations in columns. The rows are the basic data, the potential, K1-K5 with the weights, the sources, the demand signals and the timeline.
- Each value shows "fakt" or "szacunek". The highest potential has the tag "najwyższy". The table hides the potential of an innovation without sources.
- The selection stays in `localStorage` (key `radar.compare.v1`) and in the URL (`compare.html?ids=...`). Thus a user can send the link.
- Without the API, the page uses the sample data. Only one sample record has the full assessment, so other columns show "brak oceny".
- Check: headless Edge on the uvicorn server with the sample data (limit of 4, card button, remove, phone width, no console errors).

## 2026-11-22 01:27, MaciejMomot (branch 13-trl-missing)

- Accept the contract changes of PR #24. Change the TRL rule to the contract: `trl: null` means "nie dotyczy", and `trl.value: null` means that the data is missing.
- `src/criteria.py`: K2 does not apply only if the field `trl` is null. A missing TRL value now widens the range, as the other criteria do.
- `web/app.js`: the card shows "nie dotyczy" only for `trl: null`. For a null `trl.value`, it shows "brak danych".
- Add a test for a missing TRL value. No sample record has a null `trl.value`, so the sample assessments do not change.

## 2026-11-22 01:22, MaciejMomot (branch 11-watchlists, issue #14)

- Add watchlists to the search page: the button "Obserwuj to wyszukiwanie" saves the query and the filters.
- The saved queries stay only in the browser (`localStorage`, key `radar.watchlists.v1`). No login and no personal data.
- The panel "Obserwowane wyszukiwania" shows the number of new results of each saved query since the last visit.
- A new result has the tag "Nowe od ostatniej wizyty". After the visit, the page records the results as seen.
- The watchlists use the same search function as the page. Thus they operate with the API and with the sample data.
- Check: headless Edge with the sample data of PR #24 (save, simulated update, new tags, reset after the visit, remove).

## 2026-11-22 03:00, MikolajRowicki (branch 06-record-schema, issue #3)

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

## 2026-11-22 01:19, MaciejMomot (branch 09-card-page, issue #6)

- Add the card page `web/innovation.html`. The code is in `web/app.js` and `web/style.css`.
- Sections: title and summary, main facts, assessment, sources, signal timeline, demand signals (BZP), description, similar innovations.
- Each field shows "fakt" (quote and source link) or "szacunek" (reason). A null TRL shows "nie dotyczy".
- The assessment table joins each criterion to the field that caused it. "Jak liczymy ocenę?" shows the scales, weights and references.
- The card shows no assessment if the innovation has no sources (`AGENTS.md`, rule 1).
- Add `GET /api/criteria` in `src/app.py`. It returns `CRITERIA` from `src/criteria.py`, so the web page has no copy of the criteria.
- The page calls `GET /api/innovations/{id}`. If the API does not exist yet (`/api/sources` gives 404), the page uses `web/sample/innovation.json`.
- Links from the data use only http and https.
- Check: headless Edge with a test card (desktop and phone width, no console errors).

## 2026-11-22 01:16, MaciejMomot (branch 07-search-page, issue #5)

- Make the search page: `web/index.html`, `web/app.js`, `web/style.css`. Plain HTML and JS, no library, no build step.
- Add `web/config.json`: the default voivodeship and the search examples. Thus the code has no region.
- The page calls `GET /api/search`. If the API gives 404, the page uses `web/sample/search.json` (issue #3), filters it in the browser and shows a notice.
- The first view shows the default voivodeship. A search with a phrase covers all of Poland, if the user did not select a voivodeship.
- The page accepts a FieldValue or a plain value in each field. A tag with an estimate shows "szacunek" and the reason.
- The page builds the DOM with `textContent` only. Thus text from the sources cannot inject HTML.
- Check: headless Edge with test data (default view, search, filter, back button, no console errors).

## 2026-11-22 01:12, MaciejMomot (branch 05-readme, issue #16)

- Write the structure and the first full text of `README.md` in Polish: problem, solution, process, main functions, user groups, data sources, criteria and rules, assumptions and limits, scale-up, security, integration, development, license.
- Keep the start procedure and the license table of MikolajRowicki.
- Open items: MikolajRowicki checks the data sources part. Before the submission, check that each function in the README operates (comparison, CSV export, watchlists).

## 2026-11-22 01:10, MikolajRowicki (branch 04-app-skeleton, issue #2)

- Add the application skeleton: `src/app.py` (FastAPI, `GET /api/health`, static files from `web/`), `web/index.html`, `tests/test_app.py`.
- Add `requirements.in`, `requirements-dev.in` and the lock `requirements.txt`. PyTorch and sentence-transformers come later with the search (issue #9).
- Decisions: the web page is static HTML and JS that calls the JSON API (no Jinja2). The start command is `uv run --no-project uvicorn src.app:app --reload`.
- Check: sqlite-vec 0.1.9 and FTS5 load on Python 3.13 (Windows). All licenses are permissive, except certifi (MPL-2.0, a transitive dependency of httpx, used without change).
- Add `README.md` with the start procedure and the license table.

## 2026-11-22 00:56, MaciejMomot (branch 03-criteria-module, issue #4)

- Add `src/criteria.py`: the criteria K1-K5 with Polish names, scales, weights and references (`CRITERIA`), and the function `assess()`.
- `assess()` gives `potential`, `low`, `high`, `confidence`, `fact_share`, `criteria_version`, `criteria` and `missing`.
- Decisions:
  - A TRL value of null means "nie dotyczy". The weight of K2 then goes to the other criteria in proportion.
  - An unknown value of another criterion gives a range: 0 for `low`, 5 for `high`.
  - `potential` uses only the known criteria. Thus it is always in the range. If no criterion is known, `potential` is null.
  - Each entry of `criteria` has `value`, `score` (0-5), `weight` (after the change of weights), `points`, `kind` and `applicable`. This adds fields to the contract of issue #3.
- Add `estimate_implementation_level(text)` and `estimate_novelty(text)`: rules with Polish keywords, without AI. A plan ("zostanie wdrożony") counts as a concept. The evidence is always an exact part of the text.
- Add `tests/test_criteria.py` (41 tests).

## 2026-11-22 00:40, MikolajRowicki (branch 02-web-sources)

- Change the second team member in `AGENTS.md` to `MaciejMomot` (odd numbers).
- Deadline of the project: 2026-11-22 10:00.

## 2026-11-22 00:35, MikolajRowicki (branch 02-web-sources)

- Record decisions in `docs/project.md`: all user groups of the FAQ, main flow (phrase, recommendations, card), all of Poland with Podkarpackie first, summaries without a language model at the start, source of the weights.

## 2026-11-22 00:25, MikolajRowicki (branch 02-web-sources)

- Research how venture capital funds find projects. Add to `docs/project.md`: signal timeline, watchlists and alerts, arguments for the pitch (PFR Starter Science, EQT Motherbrain), hit rate and coverage.

## 2026-11-22 00:15, MikolajRowicki (branch 02-web-sources)

- Add `data/web_sources.csv`: 43 web sources in 8 categories, with the HTTP check and the crawl strategy of each category.
- Test the crawler on the 35 sources that answered. Competitions and gov.pl aggregators give the best results. Home pages of media give noise. Record the result in `docs/project.md`, section 6.1.

## 2026-11-21 23:50, MikolajRowicki (branch 02-web-sources)

- Test the crawler on 29 sites of JST and universities in Podkarpackie (script outside the repository). Result: 52 candidates, about 7 real innovations. Record the result and the next changes in `docs/project.md`, section 6.1.

## 2026-11-21 23:30, MikolajRowicki (branch 02-web-sources)

- Add the crawler of institution web pages to `docs/project.md` as source 2 (section 6.1).
- Add the list of sources not to use: LinkedIn and Facebook, with the reasons.
- Add EPO OPS and UPRP API as later sources, if the team makes accounts.

## 2026-11-21 23:00, MikolajRowicki

- Add `docs/project.md`: the concept from the FAQ, the innovation card, the five criteria (v0.1), the data sources, the architecture, the demo and the open decisions.

## 2026-11-21 22:40, MikolajRowicki

- Read the new file `task/Radar Innowacji FAQ.pdf`. The FAQ changes the scope: discovery and assessment of existing innovations, not a platform for submissions or investors.
- Change `AGENTS.md` for the FAQ: project description, three areas, Oslo Manual definition, FAQ criteria, innovation card, facts versus estimates, user groups, regular updates.
- Remove the rules about creator data, minors and the label for AI text.

## 2026-11-21 22:10, MikolajRowicki

- Finish the final report `docs/reports/Innovation radar landscape.md`. It has the existing solutions, the data sources, the rubric draft v0.1, the stack, the legal checklist and a 15-hour plan.
- Add rules from the research to `AGENTS.md`: licenses of model weights, forbidden components, hidden personal data, AI Act rules.
- Next step: the team selects the concept and writes `docs/project.md`.

## 2026-11-21 21:46, MikolajRowicki

- Finish the research on the 3 stopped topics. All 7 notes are in `docs/research_notes/Innovation radar landscape/`:
  - `data_patents_science.md`
  - `data_public_projects.md`
  - `tech_methods_stack.md`
- Start the final report `docs/reports/Innovation radar landscape.md`.

## 2026-11-21 21:20, MikolajRowicki

- Finish 4 of 7 research notes in `docs/research_notes/Innovation radar landscape/`:
  - `poland_landscape.md`
  - `eu_global_landscape.md`
  - `assessment_frameworks.md`
  - `problem_gaps_legal.md`
- Stop the research on 3 topics before the end: patent and science data, public project data, NLP methods and stack. Do this research again.
- The final report `docs/reports/Innovation radar landscape.md` does not exist yet.

## 2026-11-21 21:15, MikolajRowicki

- Change `AGENTS.md` from the KOWR task to the PCI task "Radar innowacji". New sections: personal data and security, rules of the process, criteria of the jury. The license of the solution is EUPL-1.2.
- Change `KAGGLE.md` for this project: Python 3.13, clone of the private repository with a GitHub token, examples for embeddings and language models.
- Add `.gitignore`.
- Start the research about existing solutions, data sources, assessment criteria, methods and law. Notes go to `docs/research_notes/Innovation radar landscape/`. The report goes to `docs/reports/Innovation radar landscape.md`.
