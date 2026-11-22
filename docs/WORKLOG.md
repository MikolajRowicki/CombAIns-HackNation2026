# Work log

Add an entry after each step of work. Give the date, the time, the person and the changes. The newest entry is at the top.

## 2026-11-22 01:10, MikolajRowicki (branch 04-app-skeleton, issue #2)

- Add the application skeleton: `src/app.py` (FastAPI, `GET /api/health`, static files from `web/`), `web/index.html`, `tests/test_app.py`.
- Add `requirements.in`, `requirements-dev.in` and the lock `requirements.txt`. PyTorch and sentence-transformers come later with the search (issue #9).
- Decisions: the web page is static HTML and JS that calls the JSON API (no Jinja2). The start command is `uv run --no-project uvicorn src.app:app --reload`.
- Check: sqlite-vec 0.1.9 and FTS5 load on Python 3.13 (Windows). All licenses are permissive, except certifi (MPL-2.0, a transitive dependency of httpx, used without change).
- Add `README.md` with the start procedure and the license table.

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
