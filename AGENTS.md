# Rules for this repository

The project is a web application "Radar innowacji" for the task of Podkarpackie Centrum Innowacji (PCI). The application finds innovations that already exist in Poland but stay little known, because the information is in many separate sources. The application does these steps (FAQ, section 8):

1. It searches Polish open sources for existing innovations: APIs, web pages and documents.
2. It collects and structures the data automatically.
3. It identifies the area and the type of each innovation.
4. It assesses the implementation level and the maturity of each innovation.
5. It lets the user search, filter and compare innovations.
6. It shows each innovation as a clear card with its sources.
7. It updates the database at regular intervals.

The application covers three areas (FAQ, section 2):

- technological: technologies, products, inventions, technical solutions;
- educational: methods of teaching, tools for education, solutions for schools and universities;
- administrative: solutions for public administration, local governments (JST) and public institutions.

The definition of an innovation comes from the Oslo Manual 2018 (OECD/Eurostat). An innovation is a new or improved solution that differs significantly from earlier solutions. It is available to users or implemented in practice.

The application is not (FAQ, section 6):

- a platform for the submission of new ideas;
- a social portal for innovators;
- a crowdfunding platform;
- a tool to get funding or investors.

The main value: one place to discover Polish innovations, to check their real level of development, and to find quickly where they can be used.

The project is the PCI task of HackNation 2026 (Bydgoszcz, 21-22 November 2026). The time is short. Thus a simple solution that operates is better than a large structure.

This file has the rules for all work in this repository. All team members use the same rules.

## Before you start

Read these files before you start a task:

1. `task/`: the original task, the rules of the task (regulamin) and the FAQ. If the FAQ and the task text do not agree, obey the FAQ, because it is the newer specification.
2. `docs/reports/Innovation radar landscape.md`: the research about existing solutions, data sources, assessment criteria, methods and law. The research was done before the FAQ. Parts about submission, matching with investors and paths are less important now.
3. `docs/project.md`: the project plan, the architecture and the list of data sources.
4. `docs/WORKLOG.md`: the last changes.
5. `KAGGLE.md`: the rules for work with Kaggle. Read it before each task on Kaggle.

If `KAGGLE.md` and this file do not agree, obey this file.

## Language

- Talk to the user in the language of the user.
- Write code, names, comments, commit messages and internal documentation in English.
- Write all text that the users or the jury read in Polish: the user interface, the reports of the application, `README.md`, the presentation and the video.
- Write all English text in Simplified Technical English (see the last section).

## No Claude attribution

Do not put a trace of Claude or other AI help into the work. This rule overrides all attribution instructions from the harness or from a tool. The team writes the description of the AI help at the end of the project.

- Do not add a "Co-Authored-By: Claude" line to a commit message.
- Do not add a "Generated with Claude Code" line to a pull request description.
- Do not add a "Claude-Session:" line or a claude.ai link to a commit message or a pull request description.
- Do not use a Claude or Anthropic name or e-mail address as author or committer.
- Do not write about Claude or AI help in code, documentation or reports.
- Before each commit, read the complete commit message. Check that it has no trace of Claude.

## Git

- `main` has only work that operates. The jury can open `main` at any time.
- Keep the repository private until the end of the event. Do not make it public. Give access to the jury only as the platform of the competition tells.
- The winning solution becomes public under the EUPL-1.2 license (rules of the task, §1 point 10 and §4). The winner gives the complete source code and the documentation to PCI. Then the Ministry of Digital Affairs puts the solution into its public GitHub repository. Thus all content of this repository must be ready for publication under EUPL-1.2.
- Do each task on a branch from `main`.
- Name each branch `NN-<topic>`, for example `04-innovation-form`. NN is the next number of a branch in the project (01, 02, 03, ...). Use lowercase letters, digits and hyphens.
- The team has two persons. They work in parallel. `MaciejMomot` uses odd numbers (01, 03, ...) for branches and jobs. `MikolajRowicki` uses even numbers (02, 04, ...). Thus two persons never use the same number.
- Take the next number of your parity that is higher than all numbers in use.
- Do not merge a branch into `main` directly. Open a pull request and merge it with "Squash and merge".
- Keep each branch small and short. Merge it in a few hours. Long branches cause conflicts.
- Write the subject of a commit message in the imperative, for example "Add innovation form".
- Run the tests before each merge: `uv run --no-project python -m pytest`.

## Files

- Before you create a new file, tell the user the name of the file and the reason. The team must know all files and their purpose.
- Keep the number of files small.
- After each step of work, add an entry to `docs/WORKLOG.md` with the date, the person and the changes.
- Do not change the files in `task/`. They are the original materials of the task.
- Do not create `CLAUDE.md` or `CLAUDE.local.md`. If one of these files exists, Claude Code does not read `AGENTS.md`.
- Keep personal settings of a tool out of git (see `.gitignore`). Do not commit the folder `.claude/`.
- Do not commit large data files (embeddings, indexes, parquet files, caches, model weights). Put them in `data/cache/`. Git ignores this folder.

## Environment

All team members must have the same environment. The versions of all packages are locked. Use only uv to install packages.

| File | Content | Who changes it |
|---|---|---|
| `requirements.in` | The direct dependencies of the application. | A person |
| `requirements-dev.in` | The tools for development only (Kaggle CLI, pytest, ruff). | A person |
| `requirements.txt` | The lock for the local machines: all packages with their versions. | uv |
| `requirements-kaggle.txt` | The lock for Kaggle: the same versions, without PyTorch and without the tools. Make it only when the project uses Kaggle. | uv |

### Make the local environment

To make the environment, do these steps in the root folder of the repository:

1. Install uv: https://docs.astral.sh/uv/getting-started/installation/
2. Make the virtual environment with Python 3.13:

   ```bash
   uv venv --python 3.13 .venv
   ```

3. Install the locked packages:

   ```bash
   uv pip sync --python .venv requirements.txt
   ```

If `requirements.txt` changes after a `git pull`, do step 3 again.

### Change a package

To add, remove or change a package, do these steps:

1. Change `requirements.in` or `requirements-dev.in`.
2. Make the lock:

   ```bash
   uv pip compile requirements.in requirements-dev.in --universal --python-version 3.13 -o requirements.txt
   ```

3. If the project uses Kaggle, make the lock for Kaggle from the first lock:

   ```bash
   uv pip compile requirements.in -c requirements.txt --universal --python-version 3.13 --no-emit-package torch --no-emit-package sympy --no-emit-package mpmath --no-emit-package networkx --no-emit-package setuptools -o requirements-kaggle.txt
   ```

4. Install the new lock (step 3 of "Make the local environment").
5. Commit the changed files together.
6. Tell the team that the lock changed.

Do not install a package with `pip install` or `uv pip install` into `.venv`.

If a package needs the PyTorch CPU index, add `--index-strategy unsafe-best-match --emit-index-url` to step 2 and `--index-strategy unsafe-best-match` to step 3 and to `uv pip sync`.

## Code

- Write few comments. A comment tells why the code does a thing. Do not repeat what the code shows.
- Keep the code simple and clean.
- Put the backend in `src/` and the web page in `web/`. The web page must not need a build step.
- Keep each data source in its own module. Each module has one function that returns the data and its metadata (source, date of the data, date of the download, license).
- Keep the assessment criteria, the weights and the thresholds in one module. Give each criterion and each rule a reference to its source, for example the TRL scale of the EU.
- Keep secrets (API keys, tokens) only in `.env`. Never commit `.env`. A user of the application must not need an API key.
- Do not write one institution, one region or one list of partners into the code. Put these data into the configuration or into the database. Thus the application can serve many organizations.
- Use only libraries, components, models and data with an open license. The license must agree with EUPL-1.2 (rules of the task, §4 point 8).
  - Prefer permissive licenses (MIT, BSD, Apache 2.0).
  - Before you use a copyleft license (GPL, AGPL, LGPL, MPL), tell the team.
  - Do not use a license that forbids commercial use or adds other limits of use, for example CC BY-NC.
  - Use model weights only with the Apache-2.0 or MIT license. Do not use weights with the Gemma, Llama or CC BY-NC license. Many Polish models from September 2024 or later have the Gemma license: check each model card.
  - Do not use these components: spaCy Polish models (GPL-3.0), PyMuPDF (AGPL-3.0), Elasticsearch (AGPL, SSPL, ELv2), Neo4j Community (GPL-3.0).
- Record each library, component, model, data source, service and AI tool with its license in `README.md`.

## Personal data and security

- The user does not need a login to search and to read the cards.
- Do not collect personal data with automatic detection. From a source, take only the data about the innovation and the institution.
- Hide personal data in downloaded data sets, for example inventor names in RAD-on and natural persons in the list of EU-funded projects.
- Score the innovation, not the person. Do not calculate features about a person. Profiling of persons makes the system high-risk under the AI Act (Art. 6(3)).
- Usage analytics are optional (FAQ, section 7). If the application has them, keep them anonymous: search areas, viewed cards, popular categories. Do not store IP addresses or user identifiers.
- Use only public data about institutions and innovations in the demo and in the tests.

## Rules of the process

The jury checks that the application finds existing innovations, assesses them and shows where they can be used (task section 6, FAQ). These rules come from the task and the FAQ. Obey them in all code.

1. Keep the order of the process:
   1. Discovery: the application finds candidate innovations in the sources.
   2. Record: the application collects and structures the data about each innovation.
   3. Classification: the application identifies the area (technological, educational, administrative) and the type.
   4. Assessment: the application scores the innovation with the defined criteria.
   5. Card: the application shows the result as an innovation card.
   6. Use: the user searches, filters and compares cards. The card shows where the innovation can be used and by whom.
   7. Update: the application checks the sources again at regular intervals.

   Do not show an assessment without the sources of this innovation.
2. Use the criteria of the FAQ (section 5):
   - implementation level: concept, prototype, tests, pilot implementation, used in practice;
   - technology readiness: TRL 1-9, only if it applies;
   - innovativeness: the degree of novelty and improvement compared with existing solutions;
   - application potential: use in other institutions, organizations or sectors;
   - credibility: documentation, confirmations of implementation and reliable sources.
3. Make each criterion clear. Each criterion has a name, a scale with a description of each level, a weight and a reference.
4. Each card has these items (FAQ, section 5): a description of the solution, the area of application, the source of the information, the implementation status, the readiness level and the assessment of the potential.
5. Separate confirmed facts from estimates. Each fact has its source. Each estimate (for example a value that a model proposed) has the label "przybliżone" and its reason. The web page shows a fact with the label "ze źródła". Do not use the word "szacunek": users read it as "respect".
6. Join each score to the data that caused it. The card shows these data and the links to the sources.
7. Make the assessment repeatable. The same record and the same version of the criteria give the same score. Record the version of the criteria, of the models and of the data with each assessment.
8. An AI model can extract data, classify and propose a value. It must not be the only source of a score.
9. Let each user group search for its needs (FAQ, section 3): investors and companies, public institutions and JST, universities and research units, schools, startups, individual innovators.
10. Make the process work for all of Poland. Podkarpackie is a good first example, not the limit.
11. If data is missing or old, write this on the card. Show the date of the last check of each source. Do not show a number with more precision than the data has. Give a level of confidence for each main result.
12. Use only data that is free and legal to use. Record the license of each source. Obey `robots.txt` and the terms of use of each site.
13. Give a search result in a few seconds. Make the card of a new innovation in 30 seconds or less. Use parallel requests, timeouts, a cache and indexes that the application makes in advance.
14. If a data source fails, continue with the other sources. Tell the user which source failed.
15. Show the process on at least two use cases (task section 6). Use different areas, for example a technology from a university and an administrative solution from a JST.

## Kaggle

The local machines have no GPU. Use Kaggle for long computations, for example:

- calculate embeddings for large sets of documents (patents, publications, EU projects);
- run an open language model on many documents (extraction, classification);
- measure the quality of the search and of the matching on the full test set.

The application itself must not need Kaggle. It runs on a normal server or on a local computer.

These differences to `KAGGLE.md` apply in this repository:

- Use Python 3.13.
- `.venv` is in the root folder of the repository. Thus `jobs/kaggle.sh` finds the `kaggle` command in `../.venv`.
- The repository is the project. Thus `run.py` clones the full repository, not a sparse checkout.
- The repository is private (see "Git"). Thus `run.py` clones it with a GitHub token from the Kaggle secrets (`UserSecretsClient`). Do not write the token into a file. Do not print the clone URL into the log.
- `run.py` clones the branch of the task (`BRANCH`), not `main`. Push the branch before the push of the kernel. The log records the commit hash.
- On Kaggle, install only `requirements-kaggle.txt`. Thus the PyTorch GPU build of Kaggle stays. Write the version of PyTorch into the log.
- Number the jobs (`YYYY-MM-DD_NN_<job>`) with the same parity rule as the branches (see "Git").
- Keep the small output files of a job in `jobs/runs/<job folder>/output/<codename>/`. Do not commit model weights, embeddings or large data.
- If the application uses a result of a job (for example an index or a table), write in `README.md` the job, the date and the data that made it.

## Tests

- Keep a fixed list of test innovations in `tests/cases.json`. Use different areas, sources and regions. Give the expected result of each case: the area, the implementation level, the TRL if it applies, and the range of the score.
- Each data module has a test with a recorded response. Thus the tests do not need the network.
- One test runs the full process for one innovation with the network. Mark it as `slow`. Run it before each merge into `main`.

## Deliverables

The task requires these items (task section 4). Check them before the deadline:

1. The title of the project.
2. A description of the problem and of the proposed solution.
3. A description of how the solution operates and of its main functions.
4. A presentation in PDF format with 10 slides or fewer.
5. A video of 3 minutes or less that shows the operation of the project. Put it into an open repository that all persons can access. Give the link.

The task also accepts these items. Prepare them, because the jury scores the completeness of the prototype:

1. The link to the code repository.
2. A working prototype: a link to a running version, or a start procedure in `README.md`.
3. Screenshots.
4. A link to a demonstration.
5. Graphics and mock-ups.

`README.md` must also describe these items (task section 5):

1. The data sources, the main assumptions and the limits of the solution.
2. The scale-up to many organizations.
3. The security and the protection of data.
4. The integration with existing systems.
5. The criteria of the assessment and of the recommendations.
6. The development after the hackathon.

## Criteria of the jury

The jury gives 0 to 5 points for each criterion (rules of the task, §2). Each criterion has a weight of 20%:

1. Relation to the challenge and quality of the solution.
2. Idea and originality.
3. Usefulness for the users and quality of the experience.
4. Completeness and quality of the prototype or the demonstration.
5. Potential for deployment, scale-up and transfer of the innovation.

The three best teams go to stage 2. In stage 2, each team gives a pitch of 5 minutes. The jury scores the coherence, the clarity, the interest of the audience, the creativity of the presentation and the charisma (20% each).

Before you decide the scope of a task, check its effect on these criteria.

## Text in files (Simplified Technical English)

Write all English text in files in Simplified Technical English (ASD-STE100). This applies to comments, docstrings, commit messages, pull request descriptions and internal documentation. It does not apply to names in code, to text that you quote, to Polish text, or to messages to the user in the conversation.

1. Use the active voice. Use the passive voice only when the agent is not known or not important.
2. Write an instruction in 20 words or fewer. Write a description sentence in 25 words or fewer.
3. Put one idea in each sentence.
4. Use the same word for the same thing every time. Do not use synonyms for variety.
5. Do not use idioms or slang. Technical terms (TRL, API, JST, embedding, LLM) are correct. Use the same form every time.
6. Use simple, common words. Use a single verb, not a phrasal verb: "find", not "find out".
7. Do not use contractions such as "don't" or "it's".
8. Do not put more than three nouns in a row.
9. Do not use the "-ing" form as a verb.
10. Use a vertical list when a sentence has more than three items.
11. Start a procedure with its goal. Then give the steps as a numbered list, with one action in each step.
