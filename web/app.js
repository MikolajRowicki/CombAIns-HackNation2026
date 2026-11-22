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
  for (const child of children.flat()) {
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

function renderResult(result) {
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

function initSearch(config) {
  const form = $("search-form");
  const list = $("result-list");
  const status = $("status");
  const notice = $("notice");
  const title = $("results-title");
  let voivodeshipTouched = false;

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
      list.replaceChildren(...results.map(renderResult));
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
}

function plural(n) {
  if (n === 1) return "innowację";
  const last = n % 10;
  const lastTwo = n % 100;
  return last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14) ? "innowacje" : "innowacji";
}

document.addEventListener("DOMContentLoaded", async () => {
  const config = await loadConfig();
  if ($("search-form")) initSearch(config);
});
