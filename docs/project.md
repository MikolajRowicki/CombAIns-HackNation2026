# Project plan: Radar innowacji

This file has the concept, the architecture and the data sources of the project. It follows the FAQ (`task/Radar Innowacji FAQ.pdf`). The research is in `docs/reports/Innovation radar landscape.md`.

Status: draft v0.1, 2026-11-21. The team must accept or change the decisions in the section "Open decisions".

## 1. Concept

Radar innowacji is one place to discover Polish innovations that already exist. It shows their real level of development and where they can be used.

The application does not collect submissions. It finds innovations in open sources, makes an innovation card for each one, and scores it with clear criteria. A user searches, filters and compares the cards.

Two results of the project (FAQ, section 8):

1. A user finds an existing solution for a need in less time.
2. More innovations that use Polish intellectual property (IP) are implemented.

### Originality

Other catalogues need manual entry, and each covers one sector. The research found no tool that does all of these items for Poland:

1. Automatic discovery from many Polish sources in one index (science, EU projects, administration, education).
2. A card that separates confirmed facts from estimates, with a source for each fact.
3. A transparent score of the implementation level and the potential, the same for all three areas.
4. A demand signal: the card shows public institutions that bought similar solutions (BZP notices). This shows the application potential with data, not with an opinion.
5. A duplicate check: "Czy to już istnieje?" A user describes a need in free text and gets similar existing solutions.
6. A signal timeline on each card: patent, grant, award, media note, implementation. Venture capital funds use the same method to find projects with momentum.
7. Watchlists and alerts: a user saves a query and gets new matching cards, as in the EQT Motherbrain platform.

### Arguments for the pitch

- Venture capital in Poland rarely finds projects from science. About 10% of approximately 450 investments of EU-funded funds in 2019-2026 have a science component ([xyz.pl](https://xyz.pl/vc-w-polsce-wciaz-omija-nauke-pfr-szuka-zmiany/)).
- PFR Ventures started "Starter Science". It scores the ability of funds to find ideas ([ITwiz](https://itwiz.pl/pfr-stawia-na-nauke-nowy-komponent-ma-zwiekszyc-inwestycje-vc/)). Radar innowacji gives this ability to PCI, to funds and to other centres.
- Top funds build their own data platforms for sourcing. EQT Motherbrain found 7 of approximately 50 investments of EQT Ventures ([Crunchbase](https://news.crunchbase.com/venture/venture-investors-ai-deal-sourcing/)). Radar innowacji applies this method to Polish public sources.
- Radar innowacji uses signals about innovations and institutions, not about persons. Funds also track founders, but the FAQ asks for innovations, and the AI Act limits the profiling of persons.

## 2. Scope

### Areas (FAQ, section 2)

| Area | Examples | Main sources |
|---|---|---|
| Technological | inventions, products, technical solutions | RAD-on (patents and projects), UPRP list, EPO linked data, NCBR, FE projects, web pages of universities and startups |
| Educational | methods of teaching, tools for schools and universities | Web pages of schools, competition results, FE projects, RAD-on projects |
| Administrative | solutions for public administration and JST | Web pages of JST, FE projects, "Innowacyjny Samorząd", ZMP good practices, Kohesio |

### Definition of an innovation

The definition comes from the Oslo Manual 2018. An innovation is a new or improved solution that differs significantly from earlier solutions. It is available to users or implemented.

A record that is only an idea gets the implementation level "koncepcja". The application keeps it, but with a low score. Thus the user sees the difference between an implemented solution and a plan.

### Out of scope (FAQ, section 6)

- Submission of new ideas.
- A social portal for innovators.
- Crowdfunding and funding.
- A search for investors.

## 3. Users

The user is each person who needs an innovation (FAQ, section 3). No user group has priority. The application has one search and a filter for the user group. The filter changes the default sort and the visible fields of the card.

### Main flow

1. The user writes a phrase: a topic or a need, for example "drony do monitoringu upraw" or "e-usługi w urzędzie".
2. The application shows recommended innovations: a short list of cards, sorted by relevance and potential.
3. The user opens a card and analyses the innovation: summary, criteria, sources, signal timeline, similar innovations.

The first view of the map and of the lists is Podkarpackie. The search covers all of Poland.

| User group | Typical question | Default sort and fields |
|---|---|---|
| Investors and companies | "Which Polish technologies are ready to use?" | TRL, implementation level, IP (patent) |
| Public institutions and JST | "Did another gmina already solve this problem?" | Administrative area, used in practice, region, BZP buyers |
| Universities and research units | "Who works on a similar topic?" | Similar projects, institutions, TRL |
| Schools | "Which teaching methods work in other schools?" | Educational area, credibility, region |
| Startups | "Is my idea new?" | Duplicate check, innovativeness |
| Individual innovators | "Does a similar invention exist?" | Patents, duplicate check |

## 4. Process

1. **Discovery.** Loaders download records from the data sets and APIs (section 6). The crawler reads the web pages of institutions (section 6.1). A filter keeps records that describe a solution.
2. **Record.** The application maps each record to one data schema. It removes personal data.
3. **Classification.** The application selects the area and the type. The first method is keywords and the source type. A language model proposes a value for unclear records.
4. **Assessment.** The rule module scores the five criteria (section 7).
5. **Card.** The web page shows the card (section 5).
6. **Use.** The user searches, filters and compares cards. The duplicate check finds similar cards for a free-text need.
7. **Update.** A scheduled job loads each source again. It adds new records, changes the status of old records and writes the date of the check.

## 5. Innovation card

The card has the items that the FAQ requires (section 5), plus the data for the comparison.

| Field | Example | Fact or estimate |
|---|---|---|
| Title | "System zarządzania ruchem w regionie" | Fact (source) |
| Description | Short summary of the solution | Fact if quoted; estimate if a model wrote it |
| Area and type | Administrative; process | Fact (source category) or estimate |
| Area of application | Transport, JST | Estimate with reason |
| Institution | Województwo Podkarpackie | Fact |
| Region | podkarpackie | Fact |
| Implementation status | Pilot implementation | Fact or estimate |
| Readiness level | TRL 6 (only if it applies) | Usually estimate |
| Assessment of the potential | 68/100, confidence: medium | Calculated |
| Sources | Links, date of the data, date of the last check, license | Fact |
| Similar innovations | 5 cards with the similarity value | Calculated |
| Demand signals | BZP notices for similar solutions | Fact (notice) |
| Signal timeline | 2023 patent, 2024 grant, 2025 award, 2026 media note | Fact for each event (source and date) |

### Summary

The prototype makes the summary without a language model:

1. Description from the source. The FE list, RAD-on and competition pages have descriptions. This is a fact with a quote.
2. Extractive summary. For a crawled page, an algorithm (for example TextRank) selects the 2-3 most important sentences of the text.
3. Later: a language model (Bielik) writes summaries in a batch job (Kaggle). The application stores them. The card shows them with the label "szacunek". The application does not need the model at run time.

### Facts and estimates

Each field has these parts:

- `value`: the value;
- `kind`: `fact` or `estimate`;
- `source`: the link to the source and the date;
- `evidence`: a short quote from the source;
- `reason`: for an estimate, the reason in one sentence.

The code checks that each quote is a part of the source text. If the check fails, the field gets no value. The web page shows an estimate with the label "szacunek".

## 6. Data sources

Order of integration. All sources in the first group are free and need no key (tests of 2026-11-21, see the research report, section 2).

| Priority | Source | Content | Access | License | Area |
|---|---|---|---|---|---|
| 1 | Lista projektów FE 2021-2027 (dane.gov.pl) | About 36,500 projects with description, beneficiary, location | One XLSX | CC0 1.0 | All three |
| 2 | Web pages of institutions (crawler, section 6.1) | News and project pages of schools, JST, universities, incubators | HTTP, `robots.txt` | Short summary and link only (TDM, art. 26³) | All three |
| 3 | RAD-on open data (OPI PIB) | 19,032 patents of science units, 48,853 research projects | REST JSON | CC0 1.0 | Technological, educational |
| 4 | BZP notices (e-Zamówienia) | Purchases of public institutions | REST JSON | Free use; terms to check | Demand signal |
| 5 | NCBR "Wyszukiwarka sukcesów beneficjentów" | About 316 implemented results | One HTML page | Not stated; robots allow | Technological |
| 6 | Kohesio | EU projects 2014-2020 in Poland | Undocumented REST JSON | Probably CC BY 4.0 | All three |
| 7 | UPRP "Lista Wynalazków" (dane.gov.pl) | 139,381 Polish patent applications to 2018 | CSV | CC BY 4.0 | Technological |
| 8 | Interreg 2021-2027 (dane.gov.pl) | 207 projects with partners | XLSX | To check | Administrative |
| 9 | "Innowacyjny Samorząd", ZMP good practices | Administrative innovations | Web page | Rights of the owner: store only title, link and own summary | Administrative |

Later sources: EPO OPS (if the team makes an account), EPO linked open data, CORDIS, OpenAlex (free key), Erasmus+ results, GitHub API, UPRP API (if the team makes an account).

Sources not to use:

- UPRP e-Wyszukiwarka web page (bot protection);
- EPO Register web page (the terms forbid robots);
- PBN API (token for institutions only);
- Google Scholar (no API; the terms forbid scraping);
- LinkedIn and Facebook (the terms forbid scraping; personal data; profiling of persons under the AI Act).

### 6.1 Crawler of institution web pages

Many hidden innovations are only on the web pages of institutions, for example a robotics lab in a school or an application of a gmina. The FAQ (section 4) lists these pages as a source.

Procedure:

1. Make the seed list: the web pages of schools, JST, universities and incubators. For the demo, use one region (Podkarpackie, a few hundred addresses). Sources of the list: the BIP list of entities, school data on dane.gov.pl, ROR for universities.
2. Read the news and project pages of each site. Obey `robots.txt` and the TDM reservation. Send one request each 2 seconds or less often to one host. Use a user agent with the name of the project.
3. Extract the main text with trafilatura.
4. Filter the text: keywords (for example "robotyka", "innowacja pedagogiczna", "aplikacja", "wdrożenie", "nagroda", "konkurs"), then semantic similarity to known innovation cards.
5. Make a card from the text. Mark each field as a fact (with a quote) or an estimate.
6. Show the new cards in the view "Nowe na radarze".

Rules:

- Save the innovation and the institution, not persons. Do not save names of pupils, teachers or other persons.
- Save a short own summary and the link. Delete the raw HTML after the extraction.
- Record the date of each page check. The next update checks the page again.

Test of 2026-11-21 (29 sites of JST and universities in Podkarpackie, keyword filter, 109 s):

- 22 of 29 sites answered. 7 sites had a timeout or an error.
- The crawler read 247 pages and found 52 candidates.
- About 7 candidates are real innovations, for example "Mobilny Urzędnik" (Rzeszów), "E-usługi publiczne" (Brzozów) and a robotics class (ALO Rzeszów). About 10 more are lists of projects, which are good pages for the next level.
- The rest is noise. The keyword filter is too wide: "pracowni" also finds "pracownik", and "system" and "program" occur everywhere.
- The homepages of JST link to few schools (4 found). The seed list of schools must come from a register, not from JST pages.
- Pages with successes of pupils contain names. The extraction must remove them.

Changes after the test: classify with embeddings or a language model, not with keywords only; add a register of schools to the seed list; follow the pages "projekty" and "sukcesy" first.

The seed database of web sources is `data/web_sources.csv`. It has 43 sources in 8 categories:

| Category | Examples | Strategy |
|---|---|---|
| `competitions` | Explory, Młody Innowator, Student-Wynalazca, Polski Produkt Przyszłości, Innowacyjny Samorząd, Kierunek innowacja | Result pages of each edition; one card for each awarded project |
| `aggregator_gov` | gov.pl (nauka, edukacja, Laboratoria Przyszłości, CPPC), samorzad.gov.pl | News list pages; one format for many JST and schools |
| `local_media` | Nowiny24, Super Nowości, Rzeszów News, esanok, Korso Sanockie, Radio Rzeszów, Wspólnota | RSS or tag pages, not the home page |
| `student_groups` | Gazeta Politechniki, koła naukowe UR | Success news of groups |
| `tto` | CTT of UR, AGH, PRz | Technology offer catalogues |
| `innovation_bodies` | PCI, Aeropolis, Dolina Lotnicza | Leads only |
| `jst` | Rzeszów, Brzozów, Urząd Marszałkowski | Pages "projekty" and "aktualności" |
| `schools` | ALO Rzeszów | Pages "projekty" and "sukcesy" |

Test of 2026-11-22 on the 35 sources that answered (635 requests, 174 s):

- `competitions` give the most real innovations: Explory finalists, laureates of Innowacyjny Samorząd and Polski Produkt Przyszłości, medals of Student-Wynalazca.
- `aggregator_gov` gives good items (Liga Robotów winners, a technical school in Jasło with a grant), but also many navigation pages.
- `local_media` home pages give almost only noise (11 candidates from 160 pages). Use RSS and tag pages.
- `tto` and `innovation_bodies` home pages give pages about programs, not innovations.

Thus the crawler needs one strategy for each category, not one rule for all sites.

Other web sources with the same method: results of competitions and olympiads (for example Olimpiada Innowacji Technicznych, robotics competitions) and pages of student research groups (koła naukowe).

Each source has its own module in `src/sources/`. Each module has one function that returns the records and the metadata: source, date of the data, date of the download, license.

## 7. Assessment

The criteria come from the FAQ (section 5). The scales are version v0.1. They need a calibration with the PCI mentors.

The criteria come from the FAQ. The weights are a proposal of the team. They are not in a task document. Reasons: the FAQ stresses the real level of development and the Oslo Manual definition (implemented solutions), so K1 has the largest weight. TRL does not apply to educational and administrative innovations, so K2 has a small weight.

| ID | Criterion | Scale | Weight | Reference |
|---|---|---|---|---|
| K1 | Poziom wdrożenia | 1 koncepcja, 2 prototyp, 3 testy, 4 wdrożenie pilotażowe, 5 stosowane w praktyce | 30 | FAQ; Oslo Manual 2018 |
| K2 | Dojrzałość technologiczna | TRL 1-9; "nie dotyczy" for a non-technological innovation | 15 (0 if "nie dotyczy") | EU Horizon TRL definition |
| K3 | Innowacyjność | 1 new in the institution, 2 new in the region, 3 new in Poland, 4 new in Europe, 5 new in the world | 20 | Oslo Manual 2018 (degree of novelty) |
| K4 | Potencjał zastosowania | 0-5 points: documentation for others, known cost, no special infrastructure, use in more than one sector, demand signals (BZP) | 20 | Interreg Europe good practice; Rogers (diffusion attributes) |
| K5 | Wiarygodność | 0 no data, 1 own statement, 2 description with numbers, 3 one verifiable source, 4 two independent sources, 5 public confirmation of the implementation | 15 | FAQ; Nesta Standards of Evidence |

Rules:

1. Each value has a scale from 0 to 5. TRL changes to this scale: TRL 1-2 is 1, TRL 3-4 is 2, TRL 5-6 is 3, TRL 7-8 is 4, TRL 9 is 5.
2. If K2 does not apply, the other weights increase in proportion.
3. Potential = Σ weight × value / 5, on a scale of 0-100.
4. "Brak danych" is not 0. The score shows a range: the lowest value with 0 for unknown criteria, and the highest value with 5.
5. Confidence: the share of the weight with facts. High: 70% or more. Medium: 40% to 69%. Low: below 40%.
6. Each score shows its version of the criteria (for example "kryteria v0.1").
7. The rules and the weights are in one module: `src/criteria.py`.

## 8. Search and comparison

- Hybrid search: full-text search (SQLite FTS5, BM25) plus vector search (embeddings), joined with Reciprocal Rank Fusion.
- Filters: area, type, region, implementation level, TRL, source, date.
- Comparison: a table of 2-4 cards, with the criteria in rows.
- Duplicate check: the user writes a need. The application shows similar cards with the similarity value and the common terms.
- Similar cards: the 5 nearest cards by the embedding.
- Signal timeline: the application joins records of different sources about the same innovation (same institution and similar text). Each record becomes one event on the timeline. More independent events give a higher value of K5 (credibility).
- Watchlists and alerts: a user saves a query with filters, for example "drony, TRL 6 or more, podkarpackie". After each update, the application shows the new matching cards. The prototype shows them on the page. E-mail alerts come after the hackathon.

## 9. Architecture

```
src/
  sources/        one module for each data source, also the crawler (crawler.py)
  pipeline.py     discovery, record, classification, deduplication
  criteria.py     criteria, scales, weights, rules (one module)
  search.py       full-text and vector search, similar cards
  app.py          FastAPI: HTML pages and JSON API
web/              templates, CSS, htmx (no build step)
data/cache/       downloads, SQLite database, embeddings (not in git)
tests/            cases.json, recorded responses, tests
```

- One SQLite database with FTS5 and `sqlite-vec`.
- The application makes the index in advance. A search does not need the sources online.
- The update job is a command (`python -m src.pipeline update`). A cron entry or a scheduler starts it on a server.
- The JSON API and the CSV export let other systems use the data.

### Stack

| Function | Component | License |
|---|---|---|
| Backend | FastAPI, Jinja2, httpx | MIT, BSD-3 |
| Web page | htmx, Alpine.js, Chart.js, Leaflet | 0BSD, MIT, MIT, BSD-2 |
| Store and search | SQLite FTS5, sqlite-vec | Public domain, MIT/Apache-2.0 |
| Embeddings | `sdadas/mmlw-roberta-base` | Apache-2.0 |
| Polish lemmas | simplemma | MIT |
| Language model (option) | Bielik v3 (Ollama), only for unclear records, made in advance | Apache-2.0 |
| Web text | trafilatura, protego | Apache-2.0, BSD-3 |

Do not use model weights with the Gemma, Llama or CC BY-NC license. See `AGENTS.md`.

## 10. Demo

Use case 1, technological: a patent of Politechnika Rzeszowska from RAD-on.

1. The investor filter shows the patent with TRL and implementation level.
2. The card separates the facts (patent, institution, dates) from the estimates (TRL).
3. Similar cards show related work of other institutions.
4. Demand signals show public buyers of similar solutions.

Use case 2, administrative: a JST user writes a need, for example "system rezerwacji wizyt w urzędzie".

1. The duplicate check shows existing solutions from FE projects and "Innowacyjny Samorząd".
2. The comparison table shows two or three solutions with the criteria.
3. The card of the best solution shows the implementation level "stosowane w praktyce" and the sources.

Use case 3, educational (if time remains): a teaching method from an FE project for schools.

## 11. Measures of effectiveness

- The time to find an existing solution for a need (demo: below 1 minute).
- The number of cards and sources, and the share of cards with high confidence.
- The share of cards with the implementation level 4 or 5.
- Hit rate: the share of cards that an analyst marks as valuable (a metric of funds that use data).
- Coverage: the share of known innovations (for example laureates of a competition) that the radar found without help.
- After the hackathon: the number of contacts and implementations that started from a card.

## 12. Work plan

| Step | Person A: data and search | Person B: assessment, web page, presentation |
|---|---|---|
| 1 | Measure the speed of the embedding model; SQLite schema | `src/criteria.py`; card template |
| 2 | Loaders: FE list, RAD-on, BZP, NCBR | Search page, filters, card page |
| 3 | Classification, deduplication, embeddings, hybrid search | Comparison page, duplicate check page, user-group filter |
| 4 | Update job; tests with recorded responses | Demo use cases; Polish text; accessibility check |
| 5 | `README.md`: sources, licenses, limits, scale-up, security | Presentation (10 slides or fewer); video (3 minutes or less) |

## 13. Risks

| Risk | Action |
|---|---|
| A source fails during the demo | The index is made in advance; the card shows "źródło niedostępne" |
| A language model is too slow on the CPU | Use rules first; run the model in advance on Kaggle or not at all |
| Wrong classification | Show it as an estimate with its reason |
| Personal data in sources | Remove names of natural persons in the loader and in the crawler |
| The crawler finds few innovations or much noise | Test it early on 50 pages; keep the filter strict; show only cards with a quote |
| A site blocks the crawler | Obey the block; continue with the other sites |
| Weights without calibration | Show "kryteria v0.1" and the plan for calibration |

## 14. Open decisions

Decided on 2026-11-22:

- The user is each person who needs an innovation (FAQ, section 3). The main flow is phrase, recommendations, card.
- The search covers all of Poland. Podkarpackie is the first view.
- The prototype starts without a language model. Summaries come from the sources and from an extractive algorithm.

Open:

1. Accept the five criteria and the weights of section 7, or change them after a talk with the PCI mentors.
2. Decide on the optional usage analytics (FAQ, section 7).
