"use strict";

// Polish labels for the values of the API contract (issue #3).
const AREAS = {
  technological: "Technologiczny",
  educational: "Edukacyjny",
  administrative: "Administracyjny",
};
const LEVELS = {
  1: "Koncepcja",
  2: "Prototyp",
  3: "Testy",
  4: "Wdrożenie pilotażowe",
  5: "Stosowane w praktyce",
};
const CONFIDENCE = { high: "wysoka", medium: "średnia", low: "niska" };
// User groups of the FAQ, section 3. The API changes the default sort for each group.
const GROUPS = {
  investors: "Inwestor lub firma",
  public: "Instytucja publiczna lub JST",
  science: "Uczelnia lub jednostka naukowa",
  schools: "Szkoła",
  startups: "Startup",
  innovators: "Innowator indywidualny",
};
const VOIVODESHIPS = [
  "dolnośląskie", "kujawsko-pomorskie", "lubelskie", "lubuskie", "łódzkie", "małopolskie",
  "mazowieckie", "opolskie", "podkarpackie", "podlaskie", "pomorskie", "śląskie",
  "świętokrzyskie", "warmińsko-mazurskie", "wielkopolskie", "zachodniopomorskie",
];
const FILTERS = ["group", "area", "voivodeship", "level_min"];

const $ = (id) => document.getElementById(id);

// A field can be a FieldValue ({value, kind, ...}) or a plain value.
function val(field) {
  return field !== null && typeof field === "object" && "value" in field ? field.value : field;
}
function isEstimate(field) {
  return field !== null && typeof field === "object" && field.kind === "estimate";
}

// Build DOM nodes with textContent only, so that text from the sources cannot inject HTML.
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

function option(value, label) {
  return el("option", { value }, label);
}

// A tag shows "szacunek" in the tag itself, so that the user knows which value is an estimate.
function tag(field, cls, label) {
  if (!isEstimate(field)) return el("span", { class: `tag ${cls}` }, label);
  return el(
    "span",
    { class: `tag ${cls} tag-estimate`, title: field.reason ? `Szacunek: ${field.reason}` : "Wartość oszacowana" },
    label,
    el("span", { class: "estimate-mark" }, " · szacunek"),
  );
}

async function loadConfig() {
  try {
    const response = await fetch("config.json");
    if (response.ok) return await response.json();
  } catch (error) {
    console.warn("config.json not loaded", error);
  }
  return { default_voivodeship: "", examples: [] };
}

// Use the API. If the API does not exist yet (404), use the sample data and filter it here.
async function fetchResults(params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value) query.set(key, value);
  query.set("limit", "20");
  const response = await fetch(`api/search?${query}`);
  if (response.ok) return { data: await response.json(), sample: false };
  if (response.status !== 404) throw new Error(`API: HTTP ${response.status}`);

  const sample = await fetch("sample/search.json");
  if (!sample.ok) throw new Error("Brak API i brak danych przykładowych");
  return { data: filterSample(await sample.json(), params), sample: true };
}

function filterSample(data, params) {
  const words = (params.q || "").toLowerCase().split(/\s+/).filter((w) => w.length > 2);
  const results = (data.results || []).filter((r) => {
    const text = `${r.title} ${val(r.summary) || ""}`.toLowerCase();
    if (words.length && !words.some((w) => text.includes(w.slice(0, Math.max(4, w.length - 2))))) return false;
    if (params.area && val(r.area) !== params.area) return false;
    if (params.voivodeship && r.institution?.voivodeship !== params.voivodeship) return false;
    if (params.level_min && (val(r.implementation_level) || 0) < Number(params.level_min)) return false;
    return true;
  });
  results.sort((a, b) => (b.rank_score ?? b.potential ?? 0) - (a.rank_score ?? a.potential ?? 0));
  return { total: results.length, results };
}

function renderPotential(result) {
  const potential = result.potential;
  const confidence = CONFIDENCE[result.confidence] || "brak";
  if (potential === null || potential === undefined) {
    return el("div", { class: "potential" }, el("span", { class: "potential-value" }, "Potencjał: brak danych"));
  }
  return el(
    "div",
    { class: "potential" },
    el("span", { class: "potential-value" }, `Potencjał ${potential}/100`),
    el("span", { class: "meter", "aria-hidden": "true" }, el("span", { style: `width:${potential}%` })),
    el("span", { class: `confidence confidence-${result.confidence || "low"}` }, `pewność: ${confidence}`),
  );
}

function renderResult(result, isNew = false) {
  const area = val(result.area);
  const level = val(result.implementation_level);
  const inst = result.institution || {};
  const place = [inst.city, inst.voivodeship].filter(Boolean).join(", ");
  const href = `innovation.html?id=${encodeURIComponent(result.id)}`;

  return el(
    "li",
    { class: "result" },
    el(
      "div",
      { class: "result-tags" },
      isNew && el("span", { class: "tag tag-new" }, "Nowe od ostatniej wizyty"),
      area && tag(result.area, `tag-${area}`, AREAS[area] || area),
      level && tag(result.implementation_level, "tag-level", `Wdrożenie ${level}/5: ${LEVELS[level] || ""}`),
    ),
    el("h3", { class: "result-title" }, el("a", { href }, result.title)),
    val(result.summary) && el("p", { class: "result-summary" }, val(result.summary)),
    el("p", { class: "result-meta" }, [inst.name, place].filter(Boolean).join(" · ")),
    renderPotential(result),
  );
}

function readParams() {
  const url = new URLSearchParams(location.search);
  const params = { q: url.get("q") || "" };
  for (const key of FILTERS) params[key] = url.get(key) || "";
  return params;
}

// ---- Watchlists (saved queries) ----
// The saved queries stay only in the browser of the user (localStorage): no login and no personal data.

const WATCH_KEY = "radar.watchlists.v1";
const WATCH_SEEN_LIMIT = 500;

function loadWatches() {
  try {
    const watches = JSON.parse(localStorage.getItem(WATCH_KEY));
    return Array.isArray(watches) ? watches : [];
  } catch {
    return [];
  }
}

function saveWatches(watches) {
  try {
    localStorage.setItem(WATCH_KEY, JSON.stringify(watches));
    return true;
  } catch {
    return false;
  }
}

function cleanParams(params) {
  const clean = {};
  for (const key of ["q", ...FILTERS]) if (params[key]) clean[key] = params[key];
  return clean;
}

function watchKey(params) {
  return new URLSearchParams(cleanParams(params)).toString();
}

function describeParams(params) {
  const parts = [params.q ? `„${params.q}”` : "wszystkie innowacje"];
  if (params.area) parts.push(AREAS[params.area] || params.area);
  parts.push(params.voivodeship || "cała Polska");
  if (params.level_min) parts.push(`wdrożenie od ${params.level_min}/5`);
  if (params.group) parts.push(GROUPS[params.group] || params.group);
  return parts.join(" · ");
}

function initSearch(config) {
  const form = $("search-form");
  const list = $("result-list");
  const status = $("status");
  const notice = $("notice");
  const title = $("results-title");
  let voivodeshipTouched = false;
  let current = {};

  $("group").append(option("", "Wszyscy użytkownicy"), ...Object.entries(GROUPS).map(([k, v]) => option(k, v)));
  $("area").append(option("", "Wszystkie obszary"), ...Object.entries(AREAS).map(([k, v]) => option(k, v)));
  $("voivodeship").append(option("", "Cała Polska"), ...VOIVODESHIPS.map((v) => option(v, v)));
  $("level_min").append(option("", "Dowolny"), ...Object.entries(LEVELS).map(([k, v]) => option(k, `${k} · ${v}`)));

  for (const example of config.examples || []) {
    const button = el("button", { type: "button", class: "example" }, example);
    button.addEventListener("click", () => {
      $("q").value = example;
      form.requestSubmit();
    });
    $("examples").append(button);
  }

  $("voivodeship").addEventListener("change", () => {
    voivodeshipTouched = true;
  });
  for (const key of FILTERS) $(key).addEventListener("change", () => form.requestSubmit());

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    // The first view shows the default region. A search covers all of Poland, if the user did not select a region.
    if ($("q").value.trim() && !voivodeshipTouched && !new URLSearchParams(location.search).has("voivodeship")) {
      $("voivodeship").value = "";
    }
    const params = { q: $("q").value.trim() };
    for (const key of FILTERS) params[key] = $(key).value;
    const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v));
    history.pushState(params, "", query.toString() ? `?${query}` : "./");
    run(params);
  });

  $("watch-button").addEventListener("click", () => {
    const key = watchKey(current);
    let watches = loadWatches();
    if (watches.some((w) => w.key === key)) {
      watches = watches.filter((w) => w.key !== key);
    } else {
      const seen = [...list.querySelectorAll("[data-id]")].map((node) => node.dataset.id);
      watches.unshift({ key, params: cleanParams(current), seen, created: new Date().toISOString() });
    }
    if (!saveWatches(watches)) {
      status.textContent = "Przeglądarka nie pozwala zapisać obserwowanych wyszukiwań.";
      return;
    }
    updateWatchButton();
    renderWatchPanel();
  });

  function updateWatchButton() {
    const watched = loadWatches().some((w) => w.key === watchKey(current));
    $("watch-button").textContent = watched ? "★ Obserwujesz to wyszukiwanie" : "☆ Obserwuj to wyszukiwanie";
    $("watch-button").setAttribute("aria-pressed", watched ? "true" : "false");
  }

  function go(params) {
    apply(params);
    const query = new URLSearchParams(cleanParams(params));
    history.pushState(params, "", query.toString() ? `?${query}` : "./");
    run(params);
    $("results").focus();
  }

  // Count the new results of each saved query: results that the user did not see at the last visit.
  function renderWatchPanel() {
    const watches = loadWatches();
    $("watchlist").hidden = !watches.length;
    const items = watches.map((watch) => {
      const label = describeParams(watch.params);
      const count = el("span", { class: "watch-count" }, "sprawdzam…");
      const open = el("button", { type: "button", class: "watch-open" }, label);
      open.addEventListener("click", () => go({ q: "", group: "", area: "", voivodeship: "", level_min: "", ...watch.params }));
      const remove = el("button", { type: "button", class: "watch-remove", "aria-label": `Usuń: ${label}` }, "×");
      remove.addEventListener("click", () => {
        saveWatches(loadWatches().filter((w) => w.key !== watch.key));
        updateWatchButton();
        renderWatchPanel();
      });
      fetchResults(watch.params)
        .then(({ data }) => {
          const seen = new Set(watch.seen || []);
          const fresh = (data.results || []).filter((r) => !seen.has(r.id)).length;
          count.textContent = fresh ? `nowe od ostatniej wizyty: ${fresh}` : "brak nowych";
          count.classList.toggle("watch-count-new", fresh > 0);
        })
        .catch(() => {
          count.textContent = "nie udało się sprawdzić";
        });
      return el("li", { class: "watch" }, open, count, remove);
    });
    $("watch-list").replaceChildren(...items);
  }

  window.addEventListener("popstate", () => {
    const params = readParams();
    apply(params);
    run(params);
  });

  function apply(params) {
    $("q").value = params.q;
    for (const key of FILTERS) $(key).value = params[key];
  }

  async function run(params) {
    current = params;
    updateWatchButton();
    status.textContent = "Szukam…";
    list.replaceChildren();
    notice.hidden = true;
    title.textContent = params.q
      ? `Wyniki dla „${params.q}”`
      : params.voivodeship
        ? `Innowacje: województwo ${params.voivodeship}`
        : "Innowacje w całej Polsce";
    try {
      const { data, sample } = await fetchResults(params);
      if (sample) {
        notice.textContent = "Wyszukiwarka nie jest jeszcze połączona z bazą. Pokazuję dane przykładowe.";
        notice.hidden = false;
      }
      const results = data.results || [];
      // For a saved query, mark the results that are new since the last visit, then remember them as seen.
      const watches = loadWatches();
      const watch = watches.find((w) => w.key === watchKey(params));
      const seen = new Set(watch?.seen || []);
      list.replaceChildren(
        ...results.map((r) => {
          const node = renderResult(r, Boolean(watch) && !seen.has(r.id));
          node.dataset.id = r.id;
          return node;
        }),
      );
      if (watch) {
        watch.seen = [...new Set([...results.map((r) => r.id), ...seen])].slice(0, WATCH_SEEN_LIMIT);
        watch.last_visit = new Date().toISOString();
        saveWatches(watches);
        renderWatchPanel();
      }
      status.textContent = results.length
        ? `Znaleziono ${data.total ?? results.length} ${plural(data.total ?? results.length)}.`
        : "Brak wyników. Spróbuj innych słów, usuń filtry lub wybierz „Cała Polska”.";
    } catch (error) {
      console.error(error);
      status.textContent = "Nie udało się pobrać wyników. Spróbuj ponownie za chwilę.";
    }
  }

  const initial = readParams();
  if (!location.search) initial.voivodeship = config.default_voivodeship || "";
  apply(initial);
  run(initial);
  renderWatchPanel();
}

function plural(n) {
  if (n === 1) return "innowację";
  const last = n % 10;
  const lastTwo = n % 100;
  return last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14) ? "innowacje" : "innowacji";
}

// ---- Innovation card ----

const EVENTS = {
  grant: "Grant",
  patent: "Patent",
  award: "Nagroda",
  media: "Media",
  implementation: "Wdrożenie",
};
const INSTITUTION_KINDS = { jst: "JST", school: "szkoła", university: "uczelnia", company: "firma", other: "inna" };

// Only http and https links come from the data. Other schemes (for example javascript:) are dropped.
function safeUrl(url) {
  try {
    const parsed = new URL(url, location.href);
    return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : null;
  } catch {
    return null;
  }
}

function link(url, text) {
  const href = safeUrl(url);
  return href ? el("a", { href, target: "_blank", rel: "noopener noreferrer" }, text) : null;
}

function formatDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("pl-PL");
}

function missing(text = "brak danych") {
  return el("span", { class: "missing" }, text);
}

// Show where a value comes from: a fact has a quote and a source, an estimate has a reason.
function provenance(field) {
  if (field === null || typeof field !== "object" || !field.kind || field.value === null) return null;
  const estimate = field.kind === "estimate";
  return el(
    "div",
    { class: `provenance ${estimate ? "provenance-estimate" : "provenance-fact"}` },
    el("span", { class: `kind ${estimate ? "kind-estimate" : "kind-fact"}` }, estimate ? "szacunek" : "fakt"),
    estimate && field.reason && el("span", { class: "reason" }, field.reason),
    field.evidence && el("q", { class: "evidence" }, field.evidence),
    link(field.source_url, "źródło"),
  );
}

function fact(label, field, format = (v) => v) {
  const value = val(field);
  const shown = value === null || value === undefined || value === "" ? missing() : format(value);
  return [el("dt", {}, label), el("dd", {}, el("div", { class: "fact-value" }, shown), provenance(field))];
}

function section(title, ...children) {
  const id = `s-${title.toLowerCase().replace(/[^a-ząćęłńóśźż]+/g, "-")}`;
  return el("section", { class: "card-section", "aria-labelledby": id }, el("h2", { id }, title), ...children);
}

function renderAssessment(item, definitions) {
  const a = item.assessment;
  const sources = item.sources || [];
  // AGENTS.md, rule 1: no assessment without the sources of the innovation.
  if (!sources.length) {
    return section("Ocena potencjału", el("p", { class: "missing" }, "Ocena niedostępna: karta nie ma źródeł."));
  }
  if (!a) return section("Ocena potencjału", el("p", { class: "missing" }, "Ocena jeszcze nie została obliczona."));

  const version = a.criteria_version || "?";
  const confidence = CONFIDENCE[a.confidence] || "brak";
  const summary = el(
    "div",
    { class: "score" },
    el(
      "div",
      { class: "score-main" },
      el("span", { class: "score-value" }, a.potential ?? "?"),
      el("span", { class: "score-max" }, "/100"),
    ),
    el(
      "div",
      { class: "score-details" },
      el("p", {}, `Przedział: ${a.low}–${a.high} (zależnie od brakujących danych)`),
      el(
        "p",
        {},
        "Pewność oceny: ",
        el("strong", { class: `confidence-${a.confidence}` }, confidence),
        a.fact_share !== undefined ? ` (${a.fact_share}% wagi oparte na faktach)` : "",
      ),
      el("p", { class: "muted" }, `Kryteria ${version}`),
    ),
  );

  const rows = Object.entries(a.criteria || {}).map(([cid, entry]) => {
    const def = definitions?.[cid] || {};
    let shown;
    if (entry.applicable === false) shown = missing("nie dotyczy (waga przeniesiona na inne kryteria)");
    else if (entry.value === null || entry.value === undefined) shown = missing("brak danych");
    else shown = `${entry.value} · ${def.scale?.[entry.value] ?? ""}`;
    return el(
      "tr",
      {},
      el("th", { scope: "row" }, el("span", { class: "cid" }, cid), " ", def.name || ""),
      el("td", {}, shown),
      el("td", { class: "num" }, entry.applicable === false ? "0" : `${entry.weight}`),
      el("td", { class: "num" }, entry.points ?? "–"),
      el("td", {}, provenance(def.field ? item[def.field] : null) || (entry.kind ? entry.kind : "")),
    );
  });

  const table = el(
    "div",
    { class: "table-wrap" },
    el(
      "table",
      { class: "criteria" },
      el("caption", { class: "visually-hidden" }, "Ocena według kryteriów"),
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          el("th", { scope: "col" }, "Kryterium"),
          el("th", { scope: "col" }, "Wartość"),
          el("th", { scope: "col", class: "num" }, "Waga"),
          el("th", { scope: "col", class: "num" }, "Punkty"),
          el("th", { scope: "col" }, "Uzasadnienie"),
        ),
      ),
      el("tbody", {}, rows),
    ),
  );

  return section("Ocena potencjału", summary, table, renderMethod(definitions, version));
}

function renderMethod(definitions, version) {
  if (!definitions) return null;
  return el(
    "details",
    { class: "method" },
    el("summary", {}, `Jak liczymy ocenę? (kryteria ${version})`),
    el(
      "p",
      {},
      "Potencjał = suma (waga × wartość / 5), w skali 0–100. Brak danych to nie zero: przedział pokazuje wynik ",
      "przy najniższej i najwyższej możliwej wartości brakujących kryteriów. Wagi są propozycją zespołu i wymagają kalibracji.",
    ),
    Object.entries(definitions).map(([cid, def]) =>
      el(
        "div",
        { class: "method-criterion" },
        el("h3", {}, `${cid} · ${def.name} (waga ${def.weight})`),
        el("p", {}, def.description),
        el(
          "ol",
          { class: "scale", start: def.min },
          Object.entries(def.scale).map(([level, label]) => el("li", { value: level }, label)),
        ),
        def.items && el("p", { class: "muted" }, `Warunki: ${def.items.join("; ")}.`),
        el(
          "p",
          { class: "muted" },
          "Źródło: ",
          def.references.map((r, i) => [i ? "; " : "", r.url ? link(r.url, r.label) : r.label]),
        ),
      ),
    ),
  );
}

function renderSources(sources) {
  if (!sources?.length) return section("Źródła", el("p", { class: "missing" }, "Brak źródeł."));
  return section(
    "Źródła",
    el(
      "ul",
      { class: "sources" },
      sources.map((s) =>
        el(
          "li",
          {},
          link(s.url, s.name) || s.name,
          el(
            "span",
            { class: "muted" },
            ` · dane z: ${formatDate(s.data_date) || "brak daty"}`,
            ` · sprawdzono: ${formatDate(s.retrieved) || "brak daty"}`,
            ` · licencja: ${s.license || "nieznana"}`,
          ),
        ),
      ),
    ),
  );
}

function renderTimeline(timeline) {
  if (!timeline?.length) return section("Oś czasu sygnałów", el("p", { class: "missing" }, "Brak zarejestrowanych zdarzeń."));
  const events = [...timeline].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  return section(
    "Oś czasu sygnałów",
    el(
      "ol",
      { class: "timeline" },
      events.map((e) =>
        el(
          "li",
          {},
          el("time", { datetime: e.date }, formatDate(e.date)),
          el("span", { class: "tag" }, EVENTS[e.event] || e.event),
          link(e.source_url, e.label) || e.label,
        ),
      ),
    ),
  );
}

function renderDemand(demand) {
  const intro = el(
    "p",
    { class: "muted" },
    "Instytucje publiczne, które kupowały podobne rozwiązania (ogłoszenia w Biuletynie Zamówień Publicznych).",
  );
  if (!demand?.length) return section("Sygnały popytu", intro, el("p", { class: "missing" }, "Brak znalezionych zamówień."));
  return section(
    "Sygnały popytu",
    intro,
    el(
      "ul",
      { class: "demand" },
      demand.map((d) =>
        el("li", {}, el("strong", {}, d.buyer), ` · ${formatDate(d.date) || ""} · `, link(d.url, d.subject) || d.subject),
      ),
    ),
  );
}

function renderSimilar(similar) {
  if (!similar?.length) return null;
  return section("Podobne innowacje", el("ol", { class: "result-list" }, similar.map((r) => renderResult(r))));
}

function renderCard(item, definitions) {
  const area = val(item.area);
  const level = val(item.implementation_level);
  const inst = item.institution || {};
  const region = [inst.city, inst.voivodeship].filter(Boolean).join(", ");

  return [
    el(
      "header",
      { class: "card-header" },
      el(
        "div",
        { class: "result-tags" },
        area && tag(item.area, `tag-${area}`, AREAS[area] || area),
        level && tag(item.implementation_level, "tag-level", `Wdrożenie ${level}/5: ${LEVELS[level] || ""}`),
      ),
      el("h1", {}, item.title),
      val(item.summary) && el("p", { class: "lead" }, val(item.summary)),
      provenance(item.summary),
    ),
    section(
      "Najważniejsze informacje",
      el(
        "dl",
        { class: "facts" },
        fact("Obszar", item.area, (v) => AREAS[v] || v),
        fact("Typ innowacji", item.type),
        fact("Instytucja", inst.name ? { value: inst.name } : null, (v) =>
          inst.kind ? `${v} (${INSTITUTION_KINDS[inst.kind] || inst.kind})` : v,
        ),
        fact("Region", region ? { value: region } : null),
        fact("Status wdrożenia", item.implementation_level, (v) => `${v}/5 · ${LEVELS[v] || ""}`),
        // Contract (PR #24): a null trl means "nie dotyczy"; a null trl.value means that the data is missing.
        fact("Gotowość technologiczna", item.trl === null || item.trl === undefined ? { value: "nie dotyczy" } : item.trl, (v) =>
          typeof v === "number" ? `TRL ${v}/9` : v,
        ),
        item.application_areas?.length
          ? [el("dt", {}, "Gdzie można zastosować"), el("dd", {}, item.application_areas.join(", "))]
          : [],
      ),
      item.keywords?.length && el("p", { class: "keywords" }, item.keywords.map((k) => el("span", { class: "tag" }, k))),
    ),
    renderAssessment(item, definitions),
    renderSources(item.sources),
    renderTimeline(item.timeline),
    renderDemand(item.demand),
    item.description &&
      section(
        "Opis ze źródła",
        el("details", {}, el("summary", {}, "Pokaż pełny opis"), el("p", { class: "description" }, item.description)),
      ),
    renderSimilar(item.similar),
  ];
}

// Use the API. If the API does not exist yet, use the sample card. A 404 from a running API means "not found".
async function fetchInnovation(id) {
  const response = await fetch(`api/innovations/${encodeURIComponent(id)}`);
  if (response.ok) return { data: await response.json(), sample: false };
  if (response.status !== 404) throw new Error(`API: HTTP ${response.status}`);
  const probe = await fetch("api/sources");
  if (probe.status !== 404) return { data: null, sample: false };
  const sample = await fetch("sample/innovation.json");
  if (!sample.ok) throw new Error("Brak API i brak danych przykładowych");
  return { data: await sample.json(), sample: true };
}

async function fetchCriteria() {
  try {
    const response = await fetch("api/criteria");
    if (response.ok) return (await response.json()).criteria;
  } catch (error) {
    console.warn("criteria not loaded", error);
  }
  return null;
}

async function initCard() {
  const card = $("card");
  const notice = $("notice");
  const id = new URLSearchParams(location.search).get("id");
  if (document.referrer.startsWith(location.origin) && new URL(document.referrer).pathname.endsWith("/")) {
    $("back-link").href = document.referrer;
  }
  const show = (...nodes) => {
    card.replaceChildren(...nodes.flat().filter(Boolean));
    card.setAttribute("aria-busy", "false");
  };
  if (!id) return show(el("p", { class: "missing" }, "Brak identyfikatora innowacji w adresie strony."));

  try {
    const [{ data, sample }, definitions] = await Promise.all([fetchInnovation(id), fetchCriteria()]);
    if (!data) return show(el("p", { class: "missing" }, "Nie znaleziono innowacji o tym identyfikatorze."));
    if (sample) {
      notice.textContent = "Baza nie jest jeszcze połączona. Pokazuję przykładową kartę.";
      notice.hidden = false;
    }
    document.title = `${data.title} · Radar innowacji`;
    show(renderCard(data, definitions));
  } catch (error) {
    console.error(error);
    show(el("p", { class: "missing" }, "Nie udało się wczytać karty. Spróbuj ponownie za chwilę."));
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  if ($("card")) return initCard();
  const config = await loadConfig();
  if ($("search-form")) initSearch(config);
});
