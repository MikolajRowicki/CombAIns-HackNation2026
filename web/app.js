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
// Users read "szacunek" as "respect". Thus the labels say where the value comes from.
const KIND_LABELS = { fact: "ze źródła", estimate: "przybliżone" };
// User groups. The API changes the default sort for each group.
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

// An estimated tag has a dashed border and the reason in its title, so that the user knows the value is approximate.
function tag(field, cls, label) {
  if (!isEstimate(field)) return el("span", { class: `tag ${cls}` }, label);
  return el(
    "span",
    { class: `tag ${cls} tag-estimate`, title: `Wartość przybliżona${field.reason ? `: ${field.reason}` : ""}` },
    label,
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

const PAGE_SIZE = 20;

async function fetchResults(params, offset = 0) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value) query.set(key, value);
  query.set("limit", String(PAGE_SIZE));
  if (offset) query.set("offset", String(offset));
  const response = await fetch(`api/search?${query}`);
  if (!response.ok) throw new Error(`API: HTTP ${response.status}`);
  return { data: await response.json() };
}

// Status of each source: number of records, date of the last check and the last error (AGENTS.md, rules 11 and 14).
async function renderSourceStatus() {
  const list = $("source-list");
  const warning = $("source-notice");
  const warn = (text) => {
    if (!warning) return;
    warning.textContent = text;
    warning.hidden = false;
  };
  try {
    const response = await fetch("api/sources");
    if (!response.ok) throw new Error(`API: HTTP ${response.status}`);
    const sources = await response.json();
    if (!sources.length) {
      warn("Baza danych jest jeszcze pusta: aktualizacja źródeł nie została uruchomiona.");
      list?.replaceChildren(el("li", { class: "missing" }, "Brak źródeł w bazie."));
      return;
    }
    const failed = sources.filter((s) => s.error);
    if (failed.length) {
      warn(`Przy ostatniej aktualizacji nie odpowiedziały źródła: ${failed.map((s) => s.name).join(", ")}. Wyniki mogą być niepełne.`);
    }
    list?.replaceChildren(
      ...sources.map((s) =>
        el(
          "li",
          { class: `mini-tile${s.error ? " source-failed" : ""}` },
          el("strong", {}, s.name),
          el("div", {}, `${s.records} ${pluralPl(s.records, "rekord", "rekordy", "rekordów")}`),
          el("div", { class: "muted small" }, `sprawdzono: ${formatDate(s.last_check) || "nigdy"}`),
          s.error && el("div", { class: "source-error small" }, `błąd: ${s.error}`),
        ),
      ),
    );
  } catch (error) {
    console.error(error);
    list?.replaceChildren(el("li", { class: "missing" }, "Nie udało się pobrać stanu źródeł."));
  }
}

function renderPotential(result) {
  const potential = result.potential;
  const confidence = result.confidence || "low";
  const known = potential !== null && potential !== undefined;
  return el(
    "div",
    { class: "result-score" },
    el(
      "div",
      { class: "score-ring", style: `--p:${known ? potential : 0}`, role: "img", "aria-label": known ? `Potencjał ${potential} na 100` : "Potencjał: brak danych" },
      el("span", {}, known ? potential : "–"),
    ),
    el("div", { class: "score-label" }, "potencjał"),
    el("div", { class: `chip chip-${confidence}` }, `pewność: ${CONFIDENCE[confidence] || "brak"}`),
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
      { class: "result-body" },
      el(
        "div",
        { class: "result-tags" },
        isNew && el("span", { class: "tag tag-new" }, "Nowe od ostatniej wizyty"),
        area && tag(result.area, `tag-${area}`, AREAS[area] || area),
        level && tag(result.implementation_level, "tag-level", LEVELS[level] || ""),
      ),
      el("h3", { class: "result-title" }, el("a", { href }, result.title)),
      val(result.summary) && el("p", { class: "result-summary" }, val(result.summary)),
      el("p", { class: "result-meta" }, [inst.name, place].filter(Boolean).join(" · ")),
      compareToggle(result.id, result.title),
    ),
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
  const title = $("results-title");
  let voivodeshipTouched = false;
  let current = {};
  let loaded = 0;
  let total = 0;

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

  // The first call shows the first page. "Pokaż więcej" adds the next page to the list.
  async function run(params, append = false) {
    const more = $("more");
    if (!append) {
      current = params;
      loaded = 0;
      updateWatchButton();
      status.textContent = "Szukam…";
      list.replaceChildren();
      title.textContent = params.q
        ? `Wyniki dla „${params.q}”`
        : params.voivodeship
          ? `Innowacje: województwo ${params.voivodeship}`
          : "Innowacje w całej Polsce";
    }
    more.hidden = true;
    try {
      const { data } = await fetchResults(params, loaded);
      const results = data.results || [];
      total = data.total ?? results.length;
      // For a saved query, mark the results that are new since the last visit, then remember them as seen.
      const watches = loadWatches();
      const watch = watches.find((w) => w.key === watchKey(params));
      const seen = new Set(watch?.seen || []);
      list.append(
        ...results.map((r) => {
          const node = renderResult(r, Boolean(watch) && !seen.has(r.id));
          node.dataset.id = r.id;
          return node;
        }),
      );
      loaded += results.length;
      if (watch) {
        watch.seen = [...new Set([...results.map((r) => r.id), ...seen])].slice(0, WATCH_SEEN_LIMIT);
        watch.last_visit = new Date().toISOString();
        saveWatches(watches);
        renderWatchPanel();
      }
      status.textContent = loaded
        ? `Znaleziono ${total} ${plural(total)}. Pokazano ${loaded}.`
        : "Brak wyników. Spróbuj innych słów, usuń filtry lub wybierz „Cała Polska”.";
      more.hidden = loaded >= total || results.length < PAGE_SIZE;
    } catch (error) {
      console.error(error);
      status.textContent = "Nie udało się pobrać wyników. Spróbuj ponownie za chwilę.";
    }
  }

  $("more").addEventListener("click", () => run(current, true));

  const initial = readParams();
  if (!location.search) initial.voivodeship = config.default_voivodeship || "";
  apply(initial);
  run(initial);
  renderWatchPanel();
  renderSourceStatus();
}

// Polish plural: 1 innowacja, 2-4 innowacje, 5+ innowacji (12-14 take the last form).
function pluralPl(n, one, few, many) {
  if (n === 1) return one;
  const last = n % 10;
  const lastTwo = n % 100;
  return last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14) ? few : many;
}

function plural(n) {
  return pluralPl(n, "innowację", "innowacje", "innowacji");
}

// ---- Innovation card ----

const EVENTS = {
  grant: "Grant",
  patent: "Patent",
  award: "Nagroda",
  media: "Media",
  implementation: "Wdrożenie",
};
const INSTITUTION_KINDS = { jst: "samorząd (JST)", school: "szkoła", university: "uczelnia", company: "firma", other: "inna instytucja" };

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

// Where a value comes from, in a compact form: a label, and the reason, the quote and the link on demand.
function provenance(field) {
  if (field === null || typeof field !== "object" || !field.kind || field.value === null) return null;
  const estimate = field.kind === "estimate";
  const badge = el("span", { class: `kind ${estimate ? "kind-estimate" : "kind-fact"}` }, KIND_LABELS[field.kind]);
  const body = [
    estimate && field.reason && el("p", { class: "reason" }, field.reason),
    field.evidence && el("q", { class: "evidence" }, field.evidence),
    link(field.source_url, "Zobacz źródło"),
  ].filter(Boolean);
  if (!body.length) return el("div", { class: "provenance" }, badge);
  return el(
    "details",
    { class: "provenance" },
    el("summary", {}, badge, el("span", { class: "why" }, estimate ? "dlaczego?" : "cytat")),
    el("div", { class: "provenance-body" }, body),
  );
}

function tile(label, field, format = (v) => v, extra = null) {
  const value = val(field);
  const shown = value === null || value === undefined || value === "" ? missing() : format(value);
  return el(
    "div",
    { class: "tile" },
    el("div", { class: "tile-label" }, label),
    el("div", { class: "tile-value" }, shown),
    extra,
    provenance(field),
  );
}

function levelSteps(level) {
  return el(
    "div",
    { class: "steps", "aria-hidden": "true" },
    [1, 2, 3, 4, 5].map((n) => el("span", { class: n <= level ? "on" : null })),
  );
}

function section(title, ...children) {
  const id = `s-${title.toLowerCase().replace(/[^a-ząćęłńóśźż]+/g, "-")}`;
  return el("section", { class: "card-section", "aria-labelledby": id }, el("h2", { id }, title), ...children);
}

function renderScore(item) {
  const a = item.assessment;
  // AGENTS.md, rule 1: no assessment without the sources of the innovation.
  if (!item.sources?.length) return el("div", { class: "panel" }, missing("Ocena niedostępna: karta nie ma źródeł."));
  if (!a) return el("div", { class: "panel" }, missing("Ocena jeszcze nie została obliczona."));
  const confidence = a.confidence || "low";
  return el(
    "div",
    { class: "panel score-panel" },
    el("div", { class: "panel-label" }, "Potencjał innowacji"),
    el(
      "div",
      { class: "score-big" },
      el("span", { class: "score-value" }, a.potential ?? "–"),
      el("span", { class: "score-max" }, "/100"),
    ),
    el(
      "div",
      { class: "range", role: "img", "aria-label": `Przedział oceny od ${a.low} do ${a.high}` },
      el("span", { class: "range-band", style: `left:${a.low}%;width:${Math.max(a.high - a.low, 1)}%` }),
      a.potential !== null && a.potential !== undefined && el("span", { class: "range-mark", style: `left:${a.potential}%` }),
    ),
    el(
      "p",
      { class: "range-text" },
      a.low === a.high ? "Wszystkie kryteria mają dane." : `Przedział ${a.low}–${a.high}: zależy od brakujących danych.`,
    ),
    el(
      "p",
      { class: "confidence-line" },
      el("span", { class: `chip chip-${confidence}` }, `Pewność: ${CONFIDENCE[confidence] || "brak"}`),
      a.fact_share !== undefined && el("span", { class: "muted small" }, `${a.fact_share}% oceny ma dane ze źródła`),
    ),
    compareToggle(item.id, item.title, "Dodaj do porównania"),
  );
}

function renderCriteria(item, definitions) {
  const a = item.assessment;
  if (!a || !item.sources?.length) return null;
  const rows = Object.entries(a.criteria || {}).map(([cid, entry]) => {
    const def = definitions?.[cid] || {};
    let label;
    if (entry.applicable === false) label = missing("nie dotyczy");
    else if (entry.value === null || entry.value === undefined) label = missing("brak danych");
    else label = def.scale?.[entry.value] ?? String(entry.value);
    const width = entry.score === null || entry.score === undefined ? 0 : (entry.score / 5) * 100;
    return el(
      "li",
      { class: "criterion" },
      el(
        "div",
        { class: "criterion-head" },
        el("span", { class: "criterion-name" }, def.name || cid),
        entry.applicable !== false && el("span", { class: "criterion-weight" }, `waga ${Math.round(entry.weight)}%`),
      ),
      el("div", { class: "bar", "aria-hidden": "true" }, el("span", { style: `width:${width}%` })),
      el("div", { class: "criterion-value" }, label),
      provenance(def.field ? item[def.field] : null),
    );
  });
  return el(
    "div",
    { class: "panel" },
    el("h2", { class: "panel-title" }, "Kryteria oceny"),
    el("ul", { class: "criteria-list" }, rows),
    renderMethod(definitions),
  );
}

function renderMethod(definitions) {
  if (!definitions) return null;
  const weights = Object.values(definitions)
    .map((d) => `${d.name} ${d.weight}%`)
    .join(" · ");
  return el(
    "details",
    { class: "method" },
    el("summary", {}, "Jak liczymy ocenę?"),
    el("p", {}, "Każde kryterium ma skalę 0–5. Ocena 0–100 to suma kryteriów pomnożonych przez ich wagi."),
    el(
      "p",
      {},
      "Brak danych nie oznacza zera: wtedy pokazujemy przedział. Pewność jest wyższa, gdy więcej danych pochodzi wprost ze źródła.",
    ),
    el("p", { class: "muted small" }, `Wagi: ${weights}.`),
    el("a", { href: "about.html#ocena" }, "Szczegóły metody"),
  );
}

function renderSources(sources) {
  if (!sources?.length) return section("Źródła", missing("Brak źródeł."));
  return section(
    "Źródła",
    el(
      "ul",
      { class: "plain-list" },
      sources.map((s) =>
        el(
          "li",
          {},
          link(s.url, s.name) || s.name,
          el(
            "div",
            { class: "muted small" },
            `dane z ${formatDate(s.data_date) || "brak daty"} · sprawdzono ${formatDate(s.retrieved) || "brak daty"} · licencja ${s.license || "nieznana"}`,
          ),
        ),
      ),
    ),
  );
}

function renderTimeline(timeline) {
  if (!timeline?.length) return section("Historia", missing("Brak zarejestrowanych zdarzeń."));
  const events = [...timeline].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  return section(
    "Historia",
    el(
      "ol",
      { class: "timeline" },
      events.map((e) =>
        el(
          "li",
          {},
          el("time", { datetime: e.date }, formatDate(e.date)),
          el("span", { class: "chip" }, EVENTS[e.event] || e.event),
          el("div", {}, link(e.source_url, e.label) || e.label),
        ),
      ),
    ),
  );
}

function renderDemand(demand) {
  const intro = el(
    "p",
    { class: "muted small" },
    "Instytucje publiczne, które w ostatnich 180 dniach ogłosiły zamówienie o podobnym przedmiocie (Biuletyn Zamówień Publicznych). To przybliżenie, nie potwierdzony zakup tej innowacji.",
  );
  if (!demand?.length) return section("Kto kupuje podobne rozwiązania", intro, missing("Brak znalezionych zamówień."));
  return section(
    "Kto kupuje podobne rozwiązania",
    intro,
    el(
      "div",
      { class: "mini-tiles" },
      demand.map((d) =>
        el(
          "div",
          { class: "mini-tile" },
          el("strong", {}, d.buyer),
          el("div", { class: "muted small" }, formatDate(d.date) || ""),
          el("div", {}, link(d.url, d.subject) || d.subject),
          d.reason && el("div", { class: "reason small" }, d.reason),
        ),
      ),
    ),
  );
}

// Task section 6, points d and e: where the innovation can be used, by whom, and the next path with its measures.
function renderApplications(apps) {
  if (!apps) return null;
  const parts = [
    el("p", { class: "muted small" }, "Wartości przybliżone: wynikają z tekstu źródła, obszaru, poziomu wdrożenia i podobnych innowacji."),
  ];
  if (apps.sectors?.length) {
    parts.push(
      el(
        "div",
        { class: "mini-tiles" },
        apps.sectors.map((s) =>
          el(
            "div",
            { class: "mini-tile", title: s.reason || null },
            el("strong", {}, s.label),
            el("div", {}, s.recipients),
            s.evidence && el("q", { class: "evidence small" }, s.evidence),
          ),
        ),
      ),
    );
  }
  if (apps.audiences?.length) {
    parts.push(
      el("h3", {}, "Dla kogo"),
      el("p", { class: "chips" }, apps.audiences.map((a) => el("span", { class: "chip chip-audience", title: a.reason }, a.label))),
    );
  }
  if (apps.paths?.length) {
    parts.push(
      el("h3", {}, "Rekomendowana ścieżka"),
      el(
        "div",
        { class: "mini-tiles" },
        apps.paths.map((p) =>
          el(
            "div",
            { class: "mini-tile path" },
            el("strong", {}, p.name),
            el("div", { class: "small" }, p.reason),
            p.measures?.length && el("ul", { class: "small" }, p.measures.map((m) => el("li", {}, m))),
          ),
        ),
      ),
    );
  }
  if (apps.adopters?.length) {
    parts.push(
      el("h3", {}, "Kto ma podobne rozwiązania"),
      el(
        "ul",
        { class: "plain-list" },
        apps.adopters.map((a) =>
          el(
            "li",
            {},
            el("strong", {}, a.name),
            a.voivodeship ? ` (${a.voivodeship}): ` : ": ",
            el("a", { href: `innovation.html?id=${encodeURIComponent(a.innovation_id)}` }, a.innovation_title),
          ),
        ),
      ),
    );
  }
  return section("Gdzie można zastosować", ...parts);
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

  const hero = el(
    "header",
    { class: "card-hero" },
    el(
      "div",
      { class: "result-tags" },
      area && tag(item.area, `tag-${area}`, AREAS[area] || area),
      level && tag(item.implementation_level, "tag-level", LEVELS[level] || ""),
    ),
    el("h1", {}, item.title),
    el("p", { class: "card-meta" }, [inst.name, region].filter(Boolean).join(" · ")),
    val(item.summary) && el("p", { class: "lead" }, val(item.summary)),
    provenance(item.summary),
  );

  const tiles = el(
    "div",
    { class: "tiles" },
    tile("Obszar", item.area, (v) => AREAS[v] || v),
    tile("Status wdrożenia", item.implementation_level, (v) => LEVELS[v] || v, level ? levelSteps(level) : null),
    // Contract (PR #24): a null trl means "nie dotyczy"; a null trl.value means that the data is missing.
    tile("Gotowość technologiczna", item.trl === null || item.trl === undefined ? { value: "nie dotyczy" } : item.trl, (v) =>
      typeof v === "number" ? `TRL ${v} z 9` : v,
    ),
    tile("Typ", item.type),
    tile(
      "Instytucja",
      inst.name ? { value: inst.name } : null,
      (v) => v,
      inst.kind && el("div", { class: "tile-sub" }, INSTITUTION_KINDS[inst.kind] || inst.kind),
    ),
    tile("Region", region ? { value: region } : null),
  );

  const main = el(
    "div",
    { class: "card-main" },
    section(
      "W skrócie",
      tiles,
      item.keywords?.length > 0 && el("p", { class: "chips" }, item.keywords.map((k) => el("span", { class: "chip" }, k))),
    ),
    renderApplications(item.applications),
    renderDemand(item.demand),
    el("div", { class: "two-col" }, renderTimeline(item.timeline), renderSources(item.sources)),
    item.description &&
      section(
        "Opis ze źródła",
        el("details", {}, el("summary", {}, "Pokaż pełny opis"), el("p", { class: "description" }, item.description)),
      ),
  );
  const aside = el("aside", { class: "card-aside", "aria-label": "Ocena" }, renderScore(item), renderCriteria(item, definitions));
  return [hero, el("div", { class: "card-layout" }, main, aside), renderSimilar(item.similar)];
}

// A 404 means that the innovation is not in the database.
async function fetchInnovation(id) {
  const response = await fetch(`api/innovations/${encodeURIComponent(id)}`);
  if (response.ok) return { data: await response.json() };
  if (response.status === 404) return { data: null };
  throw new Error(`API: HTTP ${response.status}`);
}

async function fetchCriteria() {
  try {
    const response = await fetch("api/criteria");
    if (response.ok) return await response.json();
  } catch (error) {
    console.warn("criteria not loaded", error);
  }
  return null;
}

async function initCard() {
  const card = $("card");
  const id = new URLSearchParams(location.search).get("id");
  if (document.referrer.startsWith(location.origin) && new URL(document.referrer).pathname.endsWith("/")) {
    $("back-link").href = document.referrer;
  }
  const show = (...nodes) => {
    card.replaceChildren(...nodes.flat().filter(Boolean));
    card.setAttribute("aria-busy", "false");
  };
  if (!id) return show(missing("Brak identyfikatora innowacji w adresie strony."));

  try {
    const [{ data }, criteria] = await Promise.all([fetchInnovation(id), fetchCriteria()]);
    if (!data) {
      return show(
        el("p", { class: "missing" }, "Nie znaleziono innowacji o tym identyfikatorze. Mogła zostać usunięta przy aktualizacji bazy."),
        el("p", {}, el("a", { href: "./" }, "Przejdź do wyszukiwania")),
      );
    }
    document.title = `${data.title} · Radar innowacji`;
    show(renderCard(data, criteria?.criteria));
  } catch (error) {
    console.error(error);
    show(missing("Nie udało się wczytać karty. Spróbuj ponownie za chwilę."));
  }
}

// ---- About page: source status, method of the assessment, labels ----

async function initAbout() {
  renderSourceStatus();
  const box = $("criteria-list");
  const criteria = await fetchCriteria();
  if (!criteria) {
    box.replaceChildren(missing("Nie udało się pobrać kryteriów."));
    return;
  }
  $("criteria-version").textContent = criteria.version;
  box.replaceChildren(
    ...Object.entries(criteria.criteria).map(([cid, def]) =>
      el(
        "div",
        { class: "mini-tile" },
        el("div", { class: "criterion-head" }, el("strong", {}, def.name), el("span", { class: "criterion-weight" }, `waga ${def.weight}%`)),
        el("p", { class: "small" }, def.description),
        el(
          "ol",
          { class: "scale small", start: def.min },
          Object.entries(def.scale).map(([level, label]) => el("li", { value: level }, label)),
        ),
        def.items && el("p", { class: "muted small" }, `Warunki: ${def.items.join("; ")}.`),
        def.references?.length > 0 &&
          el(
            "p",
            { class: "muted small" },
            "Podstawa: ",
            def.references.map((r, i) => [i ? "; " : "", r.url ? link(r.url, r.label) : r.label]),
          ),
      ),
    ),
  );
}

// ---- Comparison of 2-4 innovations ----
// The selection stays only in the browser of the user (localStorage).

const COMPARE_KEY = "radar.compare.v1";
const COMPARE_MAX = 4;

function loadCompare() {
  try {
    const ids = JSON.parse(localStorage.getItem(COMPARE_KEY));
    return Array.isArray(ids) ? ids.filter((id) => typeof id === "string").slice(0, COMPARE_MAX) : [];
  } catch {
    return [];
  }
}

function saveCompare(ids) {
  try {
    localStorage.setItem(COMPARE_KEY, JSON.stringify(ids.slice(0, COMPARE_MAX)));
  } catch {
    // Without storage the selection lives only in the URL of the comparison page.
  }
  updateCompareBar();
}

function compareUrl(ids) {
  return `compare.html?ids=${ids.map(encodeURIComponent).join(",")}`;
}

function compareToggle(id, title, label = "Porównaj") {
  if (!id) return null;
  const input = el("input", { type: "checkbox", class: "compare-check" });
  input.checked = loadCompare().includes(id);
  input.dataset.compareId = id;
  input.addEventListener("change", () => {
    let ids = loadCompare();
    if (input.checked) {
      if (ids.length >= COMPARE_MAX) {
        input.checked = false;
        announce(`Możesz porównać najwyżej ${COMPARE_MAX} innowacje. Usuń jedną z porównania.`);
        return;
      }
      ids = [...ids.filter((x) => x !== id), id];
    } else {
      ids = ids.filter((x) => x !== id);
    }
    saveCompare(ids);
    announce(input.checked ? `Dodano do porównania: ${title}` : `Usunięto z porównania: ${title}`);
  });
  return el("label", { class: "compare-toggle" }, input, ` ${label}`);
}

function announce(text) {
  const region = $("compare-live");
  if (region) region.textContent = text;
}

function updateCompareBar() {
  const bar = $("compare-bar");
  if (!bar) return;
  const ids = loadCompare();
  for (const box of document.querySelectorAll(".compare-check")) box.checked = ids.includes(box.dataset.compareId);
  bar.hidden = ids.length === 0;
  $("compare-count").textContent = `Do porównania: ${ids.length} z ${COMPARE_MAX}`;
  const go = $("compare-go");
  go.href = compareUrl(ids);
  go.classList.toggle("is-disabled", ids.length < 2);
  go.setAttribute("aria-disabled", ids.length < 2 ? "true" : "false");
  go.textContent = ids.length < 2 ? "Wybierz co najmniej 2" : "Porównaj →";
}

function initCompareBar() {
  const go = el("a", { id: "compare-go", class: "btn-primary btn-small", href: "compare.html" }, "Porównaj →");
  go.addEventListener("click", (event) => {
    if (loadCompare().length < 2) event.preventDefault();
  });
  const clear = el("button", { type: "button", class: "btn-secondary btn-small" }, "Wyczyść");
  clear.addEventListener("click", () => {
    saveCompare([]);
    announce("Wyczyszczono porównanie.");
  });
  document.body.append(
    el("p", { id: "compare-live", class: "visually-hidden", role: "status", "aria-live": "polite" }),
    el(
      "div",
      { id: "compare-bar", class: "compare-bar", role: "region", "aria-label": "Porównanie", hidden: true },
      el("div", { class: "wrap compare-bar-inner" }, el("span", { id: "compare-count" }), clear, go),
    ),
  );
  updateCompareBar();
  // Other tabs can change the selection.
  window.addEventListener("storage", (event) => {
    if (event.key === COMPARE_KEY) updateCompareBar();
  });
}

function kindBadge(field) {
  if (field === null || typeof field !== "object" || !field.kind) return null;
  const estimate = field.kind === "estimate";
  return el(
    "span",
    {
      class: `kind ${estimate ? "kind-estimate" : "kind-fact"}`,
      title: estimate ? field.reason || "Wartość oszacowana" : field.evidence || "Fakt ze źródła",
    },
    KIND_LABELS[field.kind],
  );
}

function valueCell(field, format = (v) => v) {
  const value = val(field);
  if (value === null || value === undefined || value === "") return missing();
  return [el("div", { class: "fact-value" }, format(value)), kindBadge(field)];
}

function potentialOf(item) {
  if (Array.isArray(item.sources) && !item.sources.length) return null;
  return item.assessment ? item.assessment.potential : item.potential;
}

function renderCompare(items, definitions, onRemove) {
  const scores = items.map((i) => potentialOf(i) ?? -1);
  const best = Math.max(...scores);
  // The tag "najwyższy" marks one winner only, not a tie.
  const unique = scores.filter((x) => x === best).length === 1;
  const row = (label, cell, cls = "") =>
    el("tr", { class: cls }, el("th", { scope: "row" }, label), items.map((i) => el("td", {}, cell(i))));
  const group = (label) => el("tr", { class: "compare-group" }, el("th", { colspan: items.length + 1, scope: "colgroup" }, label));

  const head = el(
    "tr",
    {},
    el("td", {}),
    items.map((i) => {
      const remove = el("button", { type: "button", class: "watch-remove", "aria-label": `Usuń z porównania: ${i.title}` }, "×");
      remove.addEventListener("click", () => onRemove(i.id));
      return el(
        "th",
        { scope: "col" },
        el("div", { class: "compare-head" }, el("a", { href: `innovation.html?id=${encodeURIComponent(i.id)}` }, i.title), remove),
      );
    }),
  );

  const potential = (i) => {
    if (Array.isArray(i.sources) && !i.sources.length) return missing("ocena niedostępna: brak źródeł");
    const a = i.assessment;
    const p = potentialOf(i);
    if (p === null || p === undefined) return missing();
    const conf = a?.confidence ?? i.confidence;
    return [
      el("div", { class: "compare-score" }, el("strong", {}, `${p}/100`), p === best && unique && el("span", { class: "tag tag-new" }, "najwyższy")),
      a && el("div", { class: "muted" }, `przedział ${a.low}–${a.high}`),
      el("div", { class: `confidence confidence-${conf || "low"}` }, `pewność: ${CONFIDENCE[conf] || "brak"}`),
    ];
  };

  const criterion = (cid, def) => (i) => {
    const entry = i.assessment?.criteria?.[cid];
    if (!entry) return missing("brak oceny");
    if (entry.applicable === false) return missing("nie dotyczy");
    if (entry.value === null || entry.value === undefined) return missing();
    return [el("div", { class: "fact-value" }, `${entry.value} · ${def.scale?.[entry.value] ?? ""}`), kindBadge(def.field ? i[def.field] : null)];
  };

  const sources = (i) => {
    if (!Array.isArray(i.sources)) return missing("zobacz kartę");
    if (!i.sources.length) return missing("brak źródeł");
    return el(
      "ul",
      { class: "compare-sources" },
      i.sources.map((s) => el("li", {}, link(s.url, s.name) || s.name, el("span", { class: "muted" }, ` · sprawdzono ${formatDate(s.retrieved) || "?"}`))),
    );
  };

  const rows = [
    group("Podstawowe informacje"),
    row("Obszar", (i) => valueCell(i.area, (v) => AREAS[v] || v)),
    row("Typ innowacji", (i) => valueCell(i.type)),
    row("Instytucja", (i) => i.institution?.name || missing()),
    row("Region", (i) => [i.institution?.city, i.institution?.voivodeship].filter(Boolean).join(", ") || missing()),
    row("Status wdrożenia", (i) => valueCell(i.implementation_level, (v) => `${v}/5 · ${LEVELS[v] || ""}`)),
    row("Gotowość technologiczna", (i) =>
      i.trl === null ? missing("nie dotyczy") : i.trl === undefined ? missing() : valueCell(i.trl, (v) => `TRL ${v}/9`),
    ),
    group("Ocena"),
    row("Potencjał", potential, "compare-potential"),
    definitions
      ? Object.entries(definitions).map(([cid, def]) => row(`${cid} · ${def.name} (waga ${def.weight})`, criterion(cid, def)))
      : [],
    group("Dowody"),
    row("Źródła", sources),
    row("Sygnały popytu (BZP)", (i) =>
      Array.isArray(i.demand) ? (i.demand.length ? `${i.demand.length} zamówień` : missing("brak")) : missing("zobacz kartę"),
    ),
    row("Oś czasu sygnałów", (i) =>
      Array.isArray(i.timeline) ? (i.timeline.length ? `${i.timeline.length} zdarzeń` : missing("brak")) : missing("zobacz kartę"),
    ),
  ];

  return el(
    "div",
    { class: "table-wrap" },
    el(
      "table",
      { class: "compare-table" },
      el("caption", { class: "visually-hidden" }, "Porównanie innowacji: innowacje w kolumnach, kryteria w wierszach"),
      el("thead", {}, head),
      el("tbody", {}, rows),
    ),
  );
}

async function initCompare() {
  const box = $("compare");
  const fromUrl = new URLSearchParams(location.search).get("ids");
  let ids = fromUrl ? fromUrl.split(",").filter(Boolean).slice(0, COMPARE_MAX) : loadCompare();
  if (fromUrl) saveCompare(ids);

  const show = (...nodes) => {
    box.replaceChildren(...nodes.flat(Infinity).filter(Boolean));
    box.setAttribute("aria-busy", "false");
  };
  const remove = (id) => {
    ids = ids.filter((x) => x !== id);
    saveCompare(ids);
    history.replaceState(null, "", compareUrl(ids));
    render();
  };

  let loaded = [];
  let definitions = null;
  async function render() {
    if (ids.length < 2) {
      return show(
        el("p", {}, "Wybierz co najmniej 2 innowacje: zaznacz „Porównaj” przy wynikach wyszukiwania lub na karcie innowacji."),
        el("p", {}, el("a", { href: "./" }, "Przejdź do wyszukiwania")),
      );
    }
    const items = ids.map((id) => loaded.find((i) => i.id === id)).filter(Boolean);
    const lost = ids.length - items.length;
    show(
      lost > 0 && el("p", { class: "missing" }, `Nie znaleziono ${lost} z wybranych innowacji.`),
      items.length ? renderCompare(items, definitions, remove) : null,
    );
  }

  try {
    const [results, defs] = await Promise.all([Promise.all(ids.map((id) => fetchInnovation(id))), fetchCriteria()]);
    definitions = defs?.criteria;
    loaded = results.map((r) => r.data).filter(Boolean);
    render();
  } catch (error) {
    console.error(error);
    show(el("p", { class: "missing" }, "Nie udało się wczytać porównania. Spróbuj ponownie za chwilę."));
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  if ($("criteria-list")) return initAbout();
  if ($("compare")) return initCompare();
  initCompareBar();
  if ($("card")) return initCard();
  const config = await loadConfig();
  if ($("search-form")) initSearch(config);
});
