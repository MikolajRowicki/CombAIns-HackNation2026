// Build the alternative presentation with a dark look: docs/presentation/Radar_innowacji_mega.pptx.
// The content is the same as in build_deck.js. This version has more charts, graphics and screenshots.
// Needs pptxgenjs, sharp, react, react-dom and react-icons (all MIT). They are not dependencies of the application.
// Usage: NODE_PATH=<folder with node_modules> node docs/presentation/build_deck_mega.js <path to apply_theme.js of the pptx tool>
// The numbers come from data/cache/radar.db of 22.11.2026. The screenshots come from the running application.

const path = require("path");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const fa = require("react-icons/fa");

const HERE = __dirname;
const IMG = path.join(HERE, "img");
const SHOTS = path.join(HERE, "..", "screenshots");
const OUT = path.join(HERE, "Radar_innowacji_mega.pptx");

// Dark radar look. Cyan and green come from the PCI colors, with more light for a dark background.
const THEME = {
  name: "Radar innowacji mega",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "07111F",
    lt1: "FFFFFF",
    dk2: "0F2137",
    lt2: "A9BCD0",
    accent1: "22C3EE",
    accent2: "7ED957",
    accent3: "FFB547",
    accent4: "FF6B8B",
    accent5: "13294A",
    accent6: "24456E",
    hlink: "22C3EE",
    folHlink: "7ED957",
  },
};
const HEX = THEME.colors;

async function png(svg) {
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

async function icon(Component, color = "FFFFFF") {
  return png(ReactDOMServer.renderToStaticMarkup(React.createElement(Component, { color: `#${color}`, size: 256 })));
}

async function crop(file, left, top, width, height) {
  const buf = await sharp(file).extract({ left, top, width, height }).png().toBuffer();
  return { data: "image/png;base64," + buf.toString("base64"), ratio: width / height };
}

// The background: dark navy, two soft glows and a faint grid.
function backgroundSvg(gx, gy, hx, hy) {
  let grid = "";
  for (let x = 0; x <= 1920; x += 80) grid += `<line x1="${x}" y1="0" x2="${x}" y2="1080"/>`;
  for (let y = 0; y <= 1080; y += 80) grid += `<line x1="0" y1="${y}" x2="1920" y2="${y}"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">
    <defs>
      <radialGradient id="a" cx="${gx}" cy="${gy}" r="0.55"><stop offset="0" stop-color="#22C3EE" stop-opacity="0.30"/><stop offset="1" stop-color="#22C3EE" stop-opacity="0"/></radialGradient>
      <radialGradient id="b" cx="${hx}" cy="${hy}" r="0.45"><stop offset="0" stop-color="#7ED957" stop-opacity="0.16"/><stop offset="1" stop-color="#7ED957" stop-opacity="0"/></radialGradient>
    </defs>
    <rect width="1920" height="1080" fill="#07111F"/>
    <g stroke="#FFFFFF" stroke-opacity="0.035" stroke-width="1">${grid}</g>
    <rect width="1920" height="1080" fill="url(#a)"/>
    <rect width="1920" height="1080" fill="url(#b)"/>
  </svg>`;
}

// The radar: rings, cross lines, a sweep and blips with a glow.
function radarSvg(blips) {
  const c = 500;
  let rings = "";
  for (const r of [480, 380, 280, 180, 80]) rings += `<circle cx="${c}" cy="${c}" r="${r}" fill="none" stroke="#22C3EE" stroke-opacity="0.45" stroke-width="3"/>`;
  const a1 = (-90 * Math.PI) / 180;
  const a2 = (-30 * Math.PI) / 180;
  const p = (a) => `${c + 480 * Math.cos(a)},${c + 480 * Math.sin(a)}`;
  let dots = "";
  for (const [x, y, r, col] of blips) {
    dots += `<circle cx="${x}" cy="${y}" r="${r * 2.6}" fill="${col}" fill-opacity="0.25" filter="url(#g)"/><circle cx="${x}" cy="${y}" r="${r}" fill="${col}"/>`;
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000">
    <defs>
      <linearGradient id="s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22C3EE" stop-opacity="0.05"/><stop offset="1" stop-color="#22C3EE" stop-opacity="0.55"/></linearGradient>
      <radialGradient id="core"><stop offset="0" stop-color="#22C3EE" stop-opacity="0.35"/><stop offset="1" stop-color="#22C3EE" stop-opacity="0"/></radialGradient>
      <filter id="g" x="-2" y="-2" width="5" height="5"><feGaussianBlur stdDeviation="12"/></filter>
    </defs>
    <circle cx="${c}" cy="${c}" r="480" fill="url(#core)"/>
    ${rings}
    <line x1="20" y1="${c}" x2="980" y2="${c}" stroke="#22C3EE" stroke-opacity="0.3" stroke-width="2"/>
    <line x1="${c}" y1="20" x2="${c}" y2="980" stroke="#22C3EE" stroke-opacity="0.3" stroke-width="2"/>
    <path d="M${c},${c} L${p(a1)} A480,480 0 0,1 ${p(a2)} Z" fill="url(#s)"/>
    <line x1="${c}" y1="${c}" x2="${p(a2).split(",")[0]}" y2="${p(a2).split(",")[1]}" stroke="#7ED957" stroke-width="5"/>
    ${dots}
    <circle cx="${c}" cy="${c}" r="14" fill="#7ED957"/>
  </svg>`;
}

// A soft glow behind a big number or an icon.
function glowSvg(color) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><defs><radialGradient id="r"><stop offset="0" stop-color="#${color}" stop-opacity="0.55"/><stop offset="1" stop-color="#${color}" stop-opacity="0"/></radialGradient></defs><circle cx="200" cy="200" r="200" fill="url(#r)"/></svg>`;
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
  pres.title = "Radar innowacji";
  pres.subject = "Zadanie PCI, HackNation 2026";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  const bgHero = await png(backgroundSvg(0.75, 0.45, 0.1, 0.95));
  const bgContent = await png(backgroundSvg(0.95, 0.0, 0.0, 1.0));
  const radarImg = await png(
    radarSvg([
      [700, 260, 14, "#7ED957"], [790, 420, 10, "#22C3EE"], [330, 300, 9, "#FFB547"], [620, 690, 12, "#7ED957"],
      [270, 620, 8, "#22C3EE"], [560, 380, 8, "#FFFFFF"], [420, 820, 9, "#FF6B8B"], [860, 640, 7, "#FFB547"],
    ]),
  );
  const glow = {
    cyan: await png(glowSvg(HEX.accent1)),
    green: await png(glowSvg(HEX.accent2)),
    amber: await png(glowSvg(HEX.accent3)),
    pink: await png(glowSvg(HEX.accent4)),
  };

  // ---- Layouts ----
  pres.defineSlideMaster({
    title: "HERO_DARK",
    background: { data: bgHero },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.45, w: 5.6, h: 1.0, fontSize: 54, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 2.55, w: 5.0, h: 1.0, fontSize: 17, color: C.background2, valign: "top", align: "left", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT_DARK",
    background: { data: bgContent },
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: 0.5, y: 0.22, w: 9, h: 0.28, fontSize: 11, bold: true, color: C.accent1, charSpacing: 3, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.48, w: 9, h: 0.6, fontSize: 30, bold: true, color: C.background1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    ],
  });

  // ---- Helpers ----
  const shadow = () => ({ type: "outer", color: "000000", opacity: 0.45, blur: 12, offset: 4, angle: 90 });

  const panel = (slide, x, y, w, h, name, fill = C.accent5) => {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w, h, rectRadius: 0.1, fill: { color: fill, transparency: 15 }, line: { color: C.accent6, width: 0.75 }, shadow: shadow(), objectName: name,
    });
  };

  const text = (slide, t, opts) => slide.addText(t, { margin: 0, isTextBox: true, valign: "top", ...opts });

  const chip = (slide, t, x, y, w, color, h = 0.3, size = 11) => {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: h / 2, fill: { color, transparency: 78 }, line: { color, width: 0.75 }, objectName: `Chip ${t}` });
    text(slide, t, { x, y, w, h, fontSize: size, bold: true, color, align: "center", valign: "middle" });
  };

  const iconCircle = async (slide, Component, x, y, size, color, glowName) => {
    if (glowName) slide.addImage({ data: glow[glowName], x: x - size * 0.45, y: y - size * 0.45, w: size * 1.9, h: size * 1.9, altText: "" });
    slide.addShape(pres.shapes.OVAL, { x, y, w: size, h: size, fill: { color, transparency: 80 }, line: { color, width: 1.25 }, objectName: "Icon circle" });
    const pad = size * 0.26;
    slide.addImage({ data: await icon(Component, HEX[colorKey(color)] || "FFFFFF"), x: x + pad, y: y + pad, w: size - 2 * pad, h: size - 2 * pad, altText: "" });
  };
  const colorKey = (scheme) => ({ [C.accent1]: "accent1", [C.accent2]: "accent2", [C.accent3]: "accent3", [C.accent4]: "accent4", [C.background1]: "lt1" })[scheme];

  const badge = (slide, n, x, y, color = C.accent2, size = 0.34) => {
    slide.addShape(pres.shapes.OVAL, { x, y, w: size, h: size, fill: { color }, line: { color: C.text1, width: 1.5 }, shadow: shadow(), objectName: `Badge ${n}` });
    text(slide, String(n), { x, y, w: size, h: size, fontSize: size > 0.4 ? 16 : 13, bold: true, color: C.text1, align: "center", valign: "middle" });
  };

  // A screenshot in a browser frame: a bar with three dots over the image.
  const browser = (slide, img, x, y, w, alt) => {
    const h = w / img.ratio;
    const bar = 0.2;
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.04, y: y - bar, w: w + 0.08, h: h + bar + 0.04, rectRadius: 0.06, fill: { color: C.text2 }, line: { color: C.accent6, width: 0.75 }, shadow: shadow(), objectName: "Browser frame" });
    ["FF6B8B", "FFB547", "7ED957"].forEach((col, i) => {
      slide.addShape(pres.shapes.OVAL, { x: x + 0.06 + i * 0.12, y: y - bar + 0.06, w: 0.08, h: 0.08, fill: { color: col }, line: { type: "none" }, objectName: "Browser dot" });
    });
    slide.addImage({ data: img.data, x, y, w, h, altText: alt });
    return h;
  };

  const doughnutGauge = (slide, value, x, y, size, color) => {
    slide.addChart(pres.charts.DOUGHNUT, [{ name: "Potencjał", labels: ["wynik", "reszta"], values: [value, 100 - value] }], {
      x, y, w: size, h: size, holeSize: 72, chartColors: [color, HEX.accent6], showLegend: false, showValue: false, showPercent: false,
      showLabel: false, dataBorder: { pt: 0, color: HEX.dk1 }, showTitle: false,
    });
  };

  const chartText = { catAxisLabelColor: "C9D6E3", valAxisLabelColor: "C9D6E3", dataLabelColor: "FFFFFF", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", catAxisLabelFontSize: 11, dataLabelFontSize: 11 };

  const search = await crop(path.join(IMG, "search.png"), 150, 0, 1620, 1080);
  const card = await crop(path.join(IMG, "card.png"), 60, 90, 1800, 1080);
  const assessment = await crop(path.join(IMG, "assessment.png"), 0, 0, 510, 900);
  const phone = await crop(path.join(SHOTS, "06-telefon.png"), 12, 12, 375, 1500);

  // ---- 1. Title ----
  pres.addSection({ title: "Wstęp" });
  let s = pres.addSlide({ masterName: "HERO_DARK", sectionTitle: "Wstęp" });
  s.addImage({ data: radarImg, x: 5.55, y: 0.45, w: 4.7, h: 4.7, altText: "Radar z punktami: znalezione innowacje" });
  text(s, "ODKRYJ  ·  OCEŃ  ·  ZASTOSUJ", { x: 0.6, y: 1.0, w: 5, h: 0.3, fontSize: 12, bold: true, color: C.accent1, charSpacing: 4, valign: "middle" });
  s.addText("Radar Innowacji", { placeholder: "title" });
  s.addText("Istniejące polskie innowacje w jednym miejscu: znalezione automatycznie, ocenione jawnie, gotowe do użycia.", { placeholder: "body" });
  [["3 498 kart", C.accent1, 1.35], ["16 województw", C.accent2, 1.55], ["8 źródeł", C.accent3, 1.1]].reduce((x, [t, col, w]) => {
    chip(s, t, x, 3.65, w, col, 0.36, 13);
    return x + w + 0.15;
  }, 0.6);
  text(s, "Zespół CombAIns", { x: 0.6, y: 4.55, w: 5, h: 0.45, fontSize: 22, bold: true, color: C.background1, valign: "middle" });
  // Labels next to the blips on the radar.
  text(s, "e-urząd · JST", { x: 8.9, y: 1.35, w: 1.1, h: 0.25, fontSize: 10, color: C.accent2, bold: true });
  text(s, "patent · uczelnia", { x: 5.55, y: 4.45, w: 1.5, h: 0.25, fontSize: 10, color: C.accent4, bold: true });
  s.addNotes(
    "Radar innowacji to jedno miejsce, w którym gmina, szkoła, uczelnia, firma czy inwestor znajdzie polskie innowacje, które już działają. " +
      "Aplikacja sama je odkrywa w otwartych źródłach, ocenia według jawnych kryteriów i pokazuje, gdzie można je zastosować.",
  );

  // ---- 2. Problem ----
  pres.addSection({ title: "Problem i rozwiązanie" });
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Problem i rozwiązanie" });
  s.addText("01 · PROBLEM", { placeholder: "kicker" });
  s.addText("Innowacje już istnieją, ale nikt ich nie widzi", { placeholder: "title" });
  const stats = [
    ["36 500", "projektów FE 2021–2027 w jednym arkuszu dane.gov.pl, bez wyszukiwarki rozwiązań", C.accent1, "cyan"],
    ["19 000+", "patentów jednostek naukowych w RAD-on, opisanych językiem prawnym", C.accent2, "green"],
    ["~10%", "inwestycji funduszy VC z udziałem środków UE ma komponent naukowy (2019–2026)", C.accent3, "amber"],
  ];
  stats.forEach(([num, label, col, g], i) => {
    const y = 1.3 + i * 1.18;
    s.addImage({ data: glow[g], x: 0.2, y: y - 0.45, w: 1.6, h: 1.6, altText: "" });
    text(s, num, { x: 0.5, y, w: 2.3, h: 0.7, fontSize: 44, bold: true, color: col, valign: "middle" });
    text(s, label, { x: 2.85, y: y + 0.03, w: 2.45, h: 0.7, fontSize: 12, color: C.background2, valign: "middle" });
  });
  // The scattered sources around a JST that cannot see them.
  panel(s, 5.55, 1.25, 3.95, 3.4, "Scattered sources");
  const cx = 7.525;
  const cy = 2.85;
  const scattered = [
    [fa.FaEuroSign, "projekty UE", -1.45, -1.05], [fa.FaCertificate, "patenty", 0.0, -1.3], [fa.FaUniversity, "uczelnie", 1.4, -1.0],
    [fa.FaLandmark, "urzędy", 1.55, 0.25], [fa.FaSchool, "szkoły", 1.0, 1.15], [fa.FaTrophy, "konkursy", -0.95, 1.15],
    [fa.FaShoppingCart, "zamówienia", -1.42, 0.2],
  ];
  for (const [Icon, label, dx, dy] of scattered) {
    s.addShape(pres.shapes.LINE, { x: Math.min(cx, cx + dx * 0.55), y: Math.min(cy, cy + dy * 0.55), w: Math.abs(dx * 0.4) || 0.001, h: Math.abs(dy * 0.4) || 0.001, flipH: dx * dy < 0, line: { color: C.accent4, width: 1, dashType: "dash", transparency: 30 }, objectName: "Broken link" });
    await iconCircle(s, Icon, cx + dx - 0.22, cy + dy - 0.3, 0.44, C.accent1);
    text(s, label, { x: cx + dx - 0.6, y: cy + dy + 0.16, w: 1.2, h: 0.22, fontSize: 10, color: C.background2, align: "center" });
  }
  await iconCircle(s, fa.FaQuestion, cx - 0.32, cy - 0.32, 0.64, C.accent4, "pink");
  text(s, "„Gmina nie wie, że inna gmina już rozwiązała ten sam problem.”", { x: 5.55, y: 4.72, w: 3.95, h: 0.4, fontSize: 13, italic: true, color: C.background1, align: "center", valign: "middle" });
  text(s, "Katalogi wymagają zgłoszeń, obejmują jeden sektor i szybko się dezaktualizują.", { x: 0.5, y: 4.85, w: 4.8, h: 0.3, fontSize: 11, color: C.accent3, valign: "middle" });
  text(s, "Źródła: dane.gov.pl, RAD-on (OPI PIB), xyz.pl na podstawie danych PFR Ventures.", { x: 0.5, y: 5.2, w: 9, h: 0.22, fontSize: 9, color: C.background2 });
  s.addNotes(
    "Dane o innowacjach istnieją, ale są rozproszone. Lista projektów FE to 36,5 tys. wierszy w jednym pliku. RAD-on ma ponad 19 tys. patentów jednostek naukowych, czyli uczelni i instytutów. " +
      "Tylko około 10% inwestycji funduszy VC finansowanych ze środków UE ma komponent naukowy. Katalogi dobrych praktyk wymagają ręcznego zgłaszania. " +
      "Skutek: gmina nie wie, że inna gmina już rozwiązała ten sam problem.",
  );

  // ---- 3. Process ----
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Problem i rozwiązanie" });
  s.addText("02 · ROZWIĄZANIE", { placeholder: "kicker" });
  s.addText("Siedem kroków od źródła do decyzji", { placeholder: "title" });
  const steps = [
    [fa.FaSearch, "Odkrywanie", "8 otwartych źródeł"],
    [fa.FaDatabase, "Rekord", "jeden schemat, bez danych osób"],
    [fa.FaTags, "Klasyfikacja", "obszar i typ"],
    [fa.FaBalanceScale, "Ocena", "5 jawnych kryteriów"],
    [fa.FaIdCard, "Karta", "„ze źródła” i „przybliżone”"],
    [fa.FaFilter, "Użycie", "szukaj, filtruj, porównaj"],
    [fa.FaSyncAlt, "Aktualizacja", "cykliczne sprawdzanie"],
  ];
  const stepW = 1.25;
  s.addShape(pres.shapes.LINE, { x: 0.5 + stepW / 2, y: 1.72, w: 6 * (stepW + 0.042), h: 0, line: { color: C.accent1, width: 2, dashType: "dash", transparency: 40 }, objectName: "Process line" });
  for (const [i, [Icon, head, body]] of steps.entries()) {
    const x = 0.5 + i * (stepW + 0.042);
    const col = i === 3 ? C.accent2 : C.accent1;
    await iconCircle(s, Icon, x + (stepW - 0.72) / 2, 1.36, 0.72, col, i === 3 ? "green" : undefined);
    badge(s, i + 1, x + stepW / 2 + 0.17, 1.22, col, 0.28);
    text(s, head, { x, y: 2.2, w: stepW, h: 0.3, fontSize: 14, bold: true, color: C.background1, align: "center" });
    text(s, body, { x, y: 2.5, w: stepW, h: 0.5, fontSize: 11, color: C.background2, align: "center" });
  }
  const kpis = [
    ["3 498", "kart innowacji z 16 województw", C.accent1, "cyan"],
    ["1 625", "kart z Podkarpacia", C.accent2, "green"],
    ["614", "kart z poziomem wdrożenia 4–5", C.accent3, "amber"],
    ["< 0,2 s", "czas wyszukiwania", C.accent4, "pink"],
  ];
  kpis.forEach(([num, label, col, g], i) => {
    const x = 0.5 + i * 2.3;
    panel(s, x, 3.3, 2.1, 1.75, `KPI ${i + 1}`);
    s.addImage({ data: glow[g], x: x + 0.15, y: 3.15, w: 1.8, h: 1.4, altText: "" });
    text(s, num, { x: x + 0.15, y: 3.5, w: 1.8, h: 0.7, fontSize: 36, bold: true, color: col, align: "center", valign: "middle" });
    text(s, label, { x: x + 0.15, y: 4.3, w: 1.8, h: 0.55, fontSize: 12, color: C.background2, align: "center" });
  });
  s.addNotes(
    "Radar sam odkrywa innowacje w ośmiu otwartych źródłach, porządkuje je w jeden schemat, klasyfikuje i ocenia. " +
      "Użytkownik niczego nie zgłasza i nie zakłada konta. Baza ma dziś 3 498 kart z 16 województw, w tym 1 625 z Podkarpacia. " +
      "Indeks powstaje z wyprzedzeniem, więc wyszukiwanie trwa ułamek sekundy. Aktualizacja wszystkich źródeł trwa około 4 minut; pierwsza, bez pamięci podręcznej, około 20 minut.",
  );

  // ---- 4. The database in numbers ----
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Problem i rozwiązanie" });
  s.addText("03 · BAZA W LICZBACH", { placeholder: "kicker" });
  s.addText("3 498 kart, gotowych do przeszukania", { placeholder: "title" });
  panel(s, 0.5, 1.25, 2.75, 3.85, "Areas");
  panel(s, 3.45, 1.25, 3.1, 3.85, "Levels");
  panel(s, 6.75, 1.25, 2.75, 3.85, "Regions");
  text(s, "Obszar", { x: 0.7, y: 1.38, w: 2.4, h: 0.3, fontSize: 14, bold: true, color: C.background1 });
  s.addChart(pres.charts.DOUGHNUT, [{ name: "Obszar", labels: ["Technologiczny", "Edukacyjny", "Administracyjny"], values: [2950, 333, 215] }], {
    x: 0.65, y: 1.7, w: 2.45, h: 2.0, holeSize: 62, chartColors: [HEX.accent1, HEX.accent2, HEX.accent3], showLegend: false,
    showValue: false, showPercent: false, showLabel: false, dataBorder: { pt: 1, color: HEX.dk2 },
  });
  text(s, "3 498", { x: 1.3, y: 2.5, w: 1.15, h: 0.4, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" });
  [["Technologiczny", "2 950", C.accent1], ["Edukacyjny", "333", C.accent2], ["Administracyjny", "215", C.accent3]].forEach(([l, v, col], i) => {
    const y = 3.85 + i * 0.37;
    s.addShape(pres.shapes.OVAL, { x: 0.75, y: y + 0.08, w: 0.14, h: 0.14, fill: { color: col }, line: { type: "none" }, objectName: `Legend ${l}` });
    text(s, l, { x: 0.98, y, w: 1.4, h: 0.3, fontSize: 12, color: C.background2, valign: "middle" });
    text(s, v, { x: 2.3, y, w: 0.8, h: 0.3, fontSize: 12, bold: true, color: C.background1, align: "right", valign: "middle" });
  });
  text(s, "Poziom wdrożenia", { x: 3.65, y: 1.38, w: 2.7, h: 0.3, fontSize: 14, bold: true, color: C.background1 });
  s.addChart(pres.charts.BAR, [{ name: "Karty", labels: ["1 Koncepcja", "2 Prototyp", "3 Testy", "4 Pilotaż", "5 Praktyka"], values: [182, 2456, 246, 555, 59] }], {
    x: 3.55, y: 1.65, w: 2.9, h: 3.35, barDir: "col", chartColors: [HEX.accent6, HEX.accent6, HEX.accent6, HEX.accent2, HEX.accent2],
    showValue: true, dataLabelPosition: "outEnd", valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
    barGapWidthPct: 45, catAxisLabelFontSize: 10, catAxisLineShow: false, ...chartText,
  });
  text(s, "Województwo", { x: 6.95, y: 1.38, w: 2.4, h: 0.3, fontSize: 14, bold: true, color: C.background1 });
  s.addChart(pres.charts.BAR, [{ name: "Karty", labels: ["pozostałe 11", "lubelskie", "dolnośląskie", "małopolskie", "mazowieckie", "podkarpackie"], values: [115, 24, 25, 46, 102, 1625] }], {
    x: 6.8, y: 1.65, w: 2.65, h: 2.6, barDir: "bar", chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd",
    valAxisHidden: true, valAxisMaxVal: 2300, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, barGapWidthPct: 40, catAxisLineShow: false, ...chartText,
  });
  text(s, "1 561 kart bez województwa w źródle, w tym 1 164 patenty EPO. Województwa nie zgadujemy.", { x: 6.95, y: 4.3, w: 2.4, h: 0.7, fontSize: 11, color: C.accent3 });
  text(s, "Wdrożenie pilotażowe lub praktyka: 614 kart (zielone słupki). Start: Podkarpacie, zasięg: cała Polska.", { x: 0.5, y: 5.2, w: 9, h: 0.25, fontSize: 11, color: C.background2, valign: "middle" });
  s.addNotes(
    "Tak wygląda baza z 22 listopada. Najwięcej kart to rozwiązania technologiczne, ale są też edukacyjne i administracyjne. " +
      "Większość kart to prototypy; 614 kart ma wdrożenie pilotażowe albo jest stosowana w praktyce. " +
      "Zaczęliśmy od Podkarpacia, ale źródła obejmują całą Polskę. Jeśli źródło nie podaje województwa, nie zgadujemy go.",
  );

  // ---- 5. Demo ----
  pres.addSection({ title: "Demo" });
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Demo" });
  s.addText("04 · DEMO", { placeholder: "kicker" });
  s.addText("Wpisz potrzebę, dostaniesz kartę innowacji", { placeholder: "title" });
  browser(s, search, 0.55, 1.45, 3.9, "Strona wyszukiwania z zapytaniem o e-usługi w urzędzie");
  browser(s, card, 3.7, 2.05, 4.0, "Karta innowacji e-urzędu z kafelkami i panelem oceny");
  const ph = 3.7;
  const pw = ph * phone.ratio;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.45 - 0.07, y: 1.3 - 0.1, w: pw + 0.14, h: ph + 0.2, rectRadius: 0.14, fill: { color: C.text1 }, line: { color: C.accent6, width: 1.5 }, shadow: shadow(), objectName: "Phone frame" });
  s.addImage({ data: phone.data, x: 8.45, y: 1.3, w: pw, h: ph, altText: "Wyszukiwanie na telefonie" });
  badge(s, 1, 0.4, 1.3, C.accent1);
  badge(s, 2, 3.55, 1.9, C.accent2);
  badge(s, 3, 8.3, 1.1, C.accent3);
  const legend = [
    [1, "156 wyników w < 0,2 s", "fraza + filtry dla 6 grup", C.accent1],
    [2, "Karta ze źródłami", "„ze źródła” = cytat + link", C.accent2],
    [3, "Na telefonie", "bez instalacji aplikacji", C.accent3],
  ];
  legend.forEach(([n, head, body, col], i) => {
    const x = 0.5 + i * 2.6;
    badge(s, n, x, 4.65, col, 0.3);
    text(s, [{ text: head, options: { bold: true, color: C.background1, breakLine: true } }, { text: body, options: { color: C.background2, fontSize: 11 } }], { x: x + 0.4, y: 4.6, w: 2.15, h: 0.55, fontSize: 13 });
  });
  s.addNotes(
    "Użytkownik wpisuje frazę lub opis potrzeby. Tu: samorząd szuka e-usług w urzędzie i dostaje 156 istniejących rozwiązań. " +
      "Filtry obejmują grupę użytkowników, obszar, województwo i minimalny poziom wdrożenia. " +
      "Karta pokazuje opis, obszar, instytucję, status wdrożenia, gotowość technologiczną i ocenę potencjału. " +
      "Każda wartość ma etykietę: „ze źródła” z cytatem i linkiem albo „przybliżone” z powodem. Strona działa też na telefonie.",
  );

  // ---- 6. Assessment ----
  pres.addSection({ title: "Ocena i dane" });
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Ocena i dane" });
  s.addText("05 · OCENA", { placeholder: "kicker" });
  s.addText("Jawna ocena według 5 kryteriów", { placeholder: "title" });
  const criteria = [
    ["K1", "Poziom wdrożenia", "koncepcja → stosowane w praktyce", 30, HEX.accent2],
    ["K3", "Innowacyjność", "nowe w regionie, w Polsce, w świecie", 20, HEX.accent1],
    ["K4", "Potencjał zastosowania", "opis, koszt, sektory, zamówienia BZP", 20, HEX.accent3],
    ["K2", "Dojrzałość (TRL)", "TRL 1–9, tylko jeśli dotyczy", 15, HEX.accent4],
    ["K5", "Wiarygodność", "liczba i jakość niezależnych źródeł", 15, "8FA3B8"],
  ];
  s.addChart(pres.charts.DOUGHNUT, [{ name: "Waga", labels: criteria.map((c) => c[1]), values: criteria.map((c) => c[3]) }], {
    x: 0.4, y: 1.25, w: 2.6, h: 2.6, holeSize: 60, chartColors: criteria.map((c) => c[4]), showLegend: false, showPercent: false, showValue: true,
    dataLabelColor: HEX.dk1, dataLabelFontSize: 12, dataLabelFontFace: "+mn-lt", dataLabelFontBold: true, dataBorder: { pt: 1, color: HEX.dk1 },
  });
  text(s, [{ text: "100", options: { fontSize: 24, bold: true, color: C.background1, breakLine: true } }, { text: "punktów", options: { fontSize: 11, color: C.background2 } }], { x: 1.15, y: 2.2, w: 1.1, h: 0.7, align: "center", valign: "middle" });
  criteria.forEach(([k, name, scale, w, col], i) => {
    const y = 1.25 + i * 0.56;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.15, y, w: 0.5, h: 0.42, rectRadius: 0.08, fill: { color: col }, line: { type: "none" }, objectName: `Criterion ${k}` });
    text(s, k, { x: 3.15, y, w: 0.5, h: 0.42, fontSize: 13, bold: true, color: C.text1, align: "center", valign: "middle" });
    text(s, [{ text: `${name}  `, options: { bold: true, color: C.background1, fontSize: 13 } }, { text: `waga ${w}`, options: { color: col, bold: true, fontSize: 11 } }, { text: "", options: { breakLine: true } }, { text: scale, options: { color: C.background2, fontSize: 11 } }], { x: 3.78, y: y - 0.04, w: 3.1, h: 0.5 });
  });
  const ah = 3.85;
  const aw = ah * assessment.ratio;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.25 - 0.06, y: 1.2 - 0.06, w: aw + 0.12, h: ah + 0.12, rectRadius: 0.06, fill: { color: C.text2 }, line: { color: C.accent6, width: 0.75 }, shadow: shadow(), objectName: "Assessment frame" });
  s.addImage({ data: assessment.data, x: 7.25, y: 1.2, w: aw, h: ah, altText: "Panel oceny na karcie z kryteriami jako paski" });
  const rules = [
    [fa.FaArrowsAltH, "Przedział, nie fałszywa precyzja", "brak danych to nie zero", C.accent1],
    [fa.FaCheckCircle, "„ze źródła” i „przybliżone”", "fakt z linkiem albo reguła z powodem", C.accent2],
    [fa.FaRedo, "Powtarzalność", "ten sam rekord = ten sam wynik; AI nie wystawia oceny", C.accent3],
  ];
  for (const [i, [Icon, head, body, col]] of rules.entries()) {
    const x = 0.5 + i * 2.25;
    await iconCircle(s, Icon, x, 4.2, 0.4, col);
    text(s, [{ text: head, options: { bold: true, color: C.background1, fontSize: 12, breakLine: true } }, { text: body, options: { color: C.background2, fontSize: 10 } }], { x: x + 0.48, y: 4.15, w: 1.72, h: 0.8 });
  }
  text(s, "Skale: TRL (Komisja Europejska), Oslo Manual 2018, Nesta, Interreg Europe. Wagi: wersja v0.1.", { x: 0.5, y: 5.2, w: 9, h: 0.22, fontSize: 9, color: C.background2, align: "right" });
  s.addNotes(
    "Pięć kryteriów: poziom wdrożenia, dojrzałość technologiczna, innowacyjność, potencjał zastosowania i wiarygodność. Wagi to jawna propozycja zespołu w wersji v0.1. " +
      "Brak danych nie oznacza zera, więc pokazujemy przedział. Potencjał zastosowania liczymy z danych: opisu, kosztu, liczby sektorów i zamówień publicznych. " +
      "Radar nie używa modelu językowego: każda wartość wynika z jawnej reguły albo wprost ze źródła, więc ten sam rekord zawsze dostaje tę samą ocenę.",
  );

  // ---- 7. Comparison ----
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Ocena i dane" });
  s.addText("06 · PORÓWNANIE", { placeholder: "kicker" });
  s.addText("Trzy karty obok siebie: wynik i jego powody", { placeholder: "title" });
  const compared = [
    {
      name: "E-urząd", inst: "Gmina Horyniec-Zdrój", area: "Administracyjny", score: 69, range: "53–76", conf: "pewność: niska", color: HEX.accent1, scheme: C.accent1,
      rows: [["K1", 4, "Pilotaż", "p"], ["K2", null, "nie dotyczy", ""], ["K3", null, "brak danych", ""], ["K4", 3, "3 z 5 warunków", "p"], ["K5", 3, "1 źródło", "z"]],
    },
    {
      name: "Wirtualny Urzędnik", inst: "Zawoja", area: "Administracyjny", score: 67, range: "67–67", conf: "pewność: średnia", color: HEX.accent2, scheme: C.accent2,
      rows: [["K1", 5, "Praktyka", "z"], ["K2", null, "nie dotyczy", ""], ["K3", 2, "Nowe w regionie", "p"], ["K4", 1, "1 z 5 warunków", "p"], ["K5", 5, "Potwierdzone", "z"]],
    },
    {
      name: "Elektrody nasadkowe", inst: "Politechnika Rzeszowska", area: "Technologiczny", score: 43, range: "28–63", conf: "pewność: niska", color: HEX.accent3, scheme: C.accent3,
      rows: [["K1", 2, "Prototyp", "p"], ["K2", null, "brak danych", ""], ["K3", null, "brak danych", ""], ["K4", 1, "1 z 5 warunków", "p"], ["K5", 4, "2 źródła", "z"]],
    },
  ];
  compared.forEach((c, i) => {
    const x = 0.5 + i * 3.05;
    panel(s, x, 1.25, 2.85, 3.85, c.name);
    doughnutGauge(s, c.score, x + 0.1, 1.3, 1.25, c.color);
    text(s, String(c.score), { x: x + 0.3, y: 1.7, w: 0.85, h: 0.45, fontSize: 22, bold: true, color: C.background1, align: "center", valign: "middle" });
    text(s, [{ text: c.name, options: { bold: true, fontSize: 13, color: C.background1, breakLine: true } }, { text: c.inst, options: { fontSize: 10, color: C.background2, breakLine: true } }, { text: `przedział ${c.range} · ${c.conf}`, options: { fontSize: 10, color: c.scheme } }], { x: x + 1.4, y: 1.4, w: 1.38, h: 1.1 });
    chip(s, c.area, x + 0.2, 2.62, 1.3, c.scheme, 0.26, 10);
    c.rows.forEach(([k, level, label, kind], r) => {
      const y = 3.03 + r * 0.4;
      text(s, k, { x: x + 0.2, y, w: 0.35, h: 0.28, fontSize: 11, bold: true, color: C.background2, valign: "middle" });
      for (let d = 0; d < 5; d++) {
        const on = level !== null && d < level;
        s.addShape(pres.shapes.OVAL, { x: x + 0.55 + d * 0.16, y: y + 0.08, w: 0.12, h: 0.12, fill: { color: on ? c.scheme : C.accent6 }, line: { type: "none" }, objectName: `${k} dot` });
      }
      text(s, label, { x: x + 1.4, y, w: 1.0, h: 0.28, fontSize: 10, color: level === null ? C.background2 : C.background1, italic: level === null, valign: "middle" });
      if (kind) {
        const col = kind === "z" ? C.accent2 : C.accent3;
        s.addShape(pres.shapes.OVAL, { x: x + 2.5, y: y + 0.07, w: 0.14, h: 0.14, fill: { color: col }, line: { type: "none" }, objectName: kind === "z" ? "ze źródła" : "przybliżone" });
      }
    });
  });
  s.addShape(pres.shapes.OVAL, { x: 0.5, y: 5.24, w: 0.14, h: 0.14, fill: { color: C.accent2 }, line: { type: "none" }, objectName: "Legend ze źródła" });
  text(s, "ze źródła", { x: 0.7, y: 5.18, w: 1, h: 0.26, fontSize: 11, color: C.background2, valign: "middle" });
  s.addShape(pres.shapes.OVAL, { x: 1.65, y: 5.24, w: 0.14, h: 0.14, fill: { color: C.accent3 }, line: { type: "none" }, objectName: "Legend przybliżone" });
  text(s, "przybliżone (reguła + powód)", { x: 1.85, y: 5.18, w: 2.4, h: 0.26, fontSize: 11, color: C.background2, valign: "middle" });
  text(s, "Porównanie 2–4 kart · link do udostępnienia · eksport CSV", { x: 4.5, y: 5.18, w: 5, h: 0.26, fontSize: 11, color: C.accent1, bold: true, align: "right", valign: "middle" });
  s.addNotes(
    "Tu mamy trzy karty z bazy obok siebie. E-urząd z Horyńca ma najwyższy wynik, 69, ale z przedziałem od 53 do 76. Nie wiemy, na ile jest nowatorski, i nie wpisujemy tam zera. " +
      "Wirtualny Urzędnik z Zawoi ma 67 i jego przedział się zamyka, bo każde kryterium ma wartość. " +
      "Zielona kropka: wartość wprost ze źródła. Pomarańczowa: wyliczyła ją reguła, a na karcie widać, dlaczego.",
  );

  // ---- 8. Use cases ----
  pres.addSection({ title: "Przypadki użycia" });
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Przypadki użycia" });
  s.addText("07 · PRZYPADKI UŻYCIA", { placeholder: "kicker" });
  s.addText("Dwa przypadki: gdzie zastosować i co dalej", { placeholder: "title" });
  // Case 1: JST.
  panel(s, 0.5, 1.25, 4.4, 3.95, "Case JST");
  await iconCircle(s, fa.FaLandmark, 0.7, 1.4, 0.5, C.accent1, "cyan");
  text(s, "Samorząd szuka e-usług", { x: 1.32, y: 1.4, w: 2.6, h: 0.5, fontSize: 16, bold: true, color: C.background1, valign: "middle" });
  doughnutGauge(s, 69, 3.85, 1.3, 0.85, HEX.accent1);
  text(s, "69", { x: 4.02, y: 1.58, w: 0.5, h: 0.3, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
  chip(s, "„e-usługi w urzędzie” · JST", 0.7, 2.1, 2.3, C.accent1, 0.28, 10);
  text(s, [
    { text: "Karta: ", options: { bold: true, color: C.background1 } }, { text: "e-urząd w Gminie Horyniec-Zdrój, wdrożenie pilotażowe, ocena 69 (53–76)", options: { color: C.background2, breakLine: true } },
    { text: "Ścieżka: ", options: { bold: true, color: C.background1 } }, { text: "replikacja w innej instytucji", options: { color: C.background2, breakLine: true } },
    { text: "Mierniki: ", options: { bold: true, color: C.background1 } }, { text: "instytucje, które przejęły rozwiązanie w 12 mies.; czas obsługi sprawy", options: { color: C.background2 } },
  ], { x: 0.7, y: 2.5, w: 4.0, h: 1.45, fontSize: 12, paraSpaceAfter: 3 });
  text(s, "Podobne wdrożenia", { x: 0.7, y: 3.98, w: 2, h: 0.25, fontSize: 11, bold: true, color: C.accent2 });
  [["Radomyśl Wielki", 1.2], ["Sędziszów Młp.", 1.1], ["Cieszanów", 0.85], ["Grębów", 0.7]].reduce((x, [t, w]) => (chip(s, t, x, 4.25, w, C.accent2, 0.26, 10), x + w + 0.08), 0.7);
  text(s, "Popyt (BZP)", { x: 0.7, y: 4.58, w: 2, h: 0.25, fontSize: 11, bold: true, color: C.accent3 });
  [["Biłgoraj", 0.8], ["Wadowice", 0.85], ["Dąbrowa Tarnowska", 1.4]].reduce((x, [t, w]) => (chip(s, t, x, 4.83, w, C.accent3, 0.26, 10), x + w + 0.08), 0.7);
  // Case 2: university.
  panel(s, 5.1, 1.25, 4.4, 3.95, "Case university");
  await iconCircle(s, fa.FaFlask, 5.3, 1.4, 0.5, C.accent3, "amber");
  text(s, "Technologia z uczelni", { x: 5.92, y: 1.4, w: 2.6, h: 0.5, fontSize: 16, bold: true, color: C.background1, valign: "middle" });
  doughnutGauge(s, 43, 8.45, 1.3, 0.85, HEX.accent3);
  text(s, "43", { x: 8.62, y: 1.58, w: 0.5, h: 0.3, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
  chip(s, "„elektroda zgrzewanie”", 5.3, 2.1, 1.9, C.accent3, 0.28, 10);
  text(s, "Bezodpadowa technologia elektrod nasadkowych, Politechnika Rzeszowska: prototyp, ocena 43 (28–63)", { x: 5.3, y: 2.5, w: 4.0, h: 0.5, fontSize: 12, color: C.background2 });
  text(s, "Dwa źródła w jednej karcie: oś czasu", { x: 5.3, y: 3.05, w: 4, h: 0.25, fontSize: 11, bold: true, color: C.accent3 });
  s.addShape(pres.shapes.LINE, { x: 5.6, y: 3.55, w: 3.4, h: 0, line: { color: C.accent3, width: 2, transparency: 30 }, objectName: "Timeline" });
  [["2017", "grant B+R"], ["2022", "zgłoszenie"], ["2025", "prawo ochronne"]].forEach(([yr, ev], i) => {
    const x = 5.6 + i * 1.7;
    s.addShape(pres.shapes.OVAL, { x: x - 0.1, y: 3.45, w: 0.2, h: 0.2, fill: { color: C.accent3 }, line: { color: C.text1, width: 1.5 }, objectName: `Event ${yr}` });
    text(s, [{ text: yr, options: { bold: true, color: C.background1, breakLine: true } }, { text: ev, options: { color: C.background2, fontSize: 10 } }], { x: x - 0.6, y: 3.7, w: 1.2, h: 0.45, fontSize: 12, align: "center" });
  });
  text(s, [
    { text: "Ścieżka: ", options: { bold: true, color: C.background1 } }, { text: "licencja lub wspólny projekt B+R", options: { color: C.background2, breakLine: true } },
    { text: "Mierniki: ", options: { bold: true, color: C.background1 } }, { text: "zapytania firm; umowa w 12 mies.; TRL +1", options: { color: C.background2, breakLine: true } },
    { text: "Kontakt: ", options: { bold: true, color: C.background1 } }, { text: "strona i e-mail uczelni, centrum transferu technologii", options: { color: C.background2 } },
  ], { x: 5.3, y: 4.25, w: 4.0, h: 0.9, fontSize: 11, paraSpaceAfter: 2 });
  s.addNotes(
    "Dwa przypadki z prawdziwych danych. Gmina szuka e-usług: radar pokazuje e-urząd w Horyńcu-Zdroju, gminy z podobnym wdrożeniem i instytucje, które kupują podobne rozwiązania. " +
      "Rekomendowana ścieżka to replikacja w innej instytucji, z miernikami skuteczności. " +
      "Drugi przypadek: technologia Politechniki Rzeszowskiej. Radar łączy projekt badawczy i prawo ochronne na wzór użytkowy w jedną kartę z osią czasu, proponuje transfer technologii i podaje oficjalny kontakt do uczelni.",
  );

  // ---- 9. Sources and deployment ----
  pres.addSection({ title: "Wartość i wdrożenie" });
  s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Wartość i wdrożenie" });
  s.addText("08 · ŹRÓDŁA I WDROŻENIE", { placeholder: "kicker" });
  s.addText("8 otwartych źródeł, gotowe dla każdego regionu", { placeholder: "title" });
  panel(s, 0.5, 1.25, 4.5, 3.95, "Sources");
  text(s, "Karty według źródła (+ 2 803 ogłoszenia BZP)", { x: 0.7, y: 1.38, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: C.background1 });
  s.addChart(pres.charts.BAR, [{ name: "Karty", labels: ["Innowacyjny Samorząd", "Interreg 2021–2027", "Kohesio 2014–2020", "NCBR: sukcesy", "RAD-on (OPI PIB)", "Projekty FE 2021–2027", "EPO Linked Open Data"], values: [42, 50, 56, 300, 927, 967, 1164] }], {
    x: 0.6, y: 1.7, w: 4.3, h: 2.85, barDir: "bar", chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd",
    valAxisHidden: true, valAxisMaxVal: 1450, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, barGapWidthPct: 35, catAxisLineShow: false, ...chartText,
  });
  [["CC0 1.0", 0.75], ["CC BY 4.0", 0.85], ["zasady KE", 0.85], ["informacja publiczna", 1.45]].reduce((x, [t, w]) => (chip(s, t, x, 4.7, w, C.accent2, 0.28, 10), x + w + 0.08), 0.7);
  const org = [
    [fa.FaMapMarkedAlt, "Region w konfiguracji", "inne centrum bez zmian w kodzie", C.accent1],
    [fa.FaPuzzlePiece, "Źródło = moduł", "nowe źródło to jedna funkcja", C.accent1],
    [fa.FaServer, "Lekka infrastruktura", "SQLite, bez GPU i opłat", C.accent2],
    [fa.FaLock, "Bezpieczeństwo", "bez logowania; dane osób ukryte", C.accent2],
    [fa.FaFileCsv, "CSV i API JSON", "do arkusza, CRM, innych systemów", C.accent3],
    [fa.FaBell, "Obserwowane wyszukiwania", "„nowe od ostatniej wizyty”", C.accent3],
    [fa.FaChartBar, "Anonimowa analityka", "popularne obszary, bez osób", C.accent4],
    [fa.FaBalanceScaleLeft, "Licencja EUPL-1.2", "tylko otwarte komponenty", C.accent4],
  ];
  for (const [i, [Icon, head, body, col]] of org.entries()) {
    const x = 5.2 + (i % 2) * 2.2;
    const y = 1.25 + Math.floor(i / 2) * 1.0;
    panel(s, x, y, 2.1, 0.88, head);
    await iconCircle(s, Icon, x + 0.12, y + 0.22, 0.44, col);
    text(s, [{ text: head, options: { bold: true, color: C.background1, fontSize: 11, breakLine: true } }, { text: body, options: { color: C.background2, fontSize: 9.5 } }], { x: x + 0.65, y: y + 0.1, w: 1.4, h: 0.7, valign: "middle" });
  }
  s.addNotes(
    "Korzystamy tylko z bezpłatnych i legalnych źródeł, bez kluczy API. Każdy rekord ma licencję i datę sprawdzenia. Awaria jednego źródła nie zatrzymuje pozostałych. " +
      "Region i źródła są w konfiguracji, a nie w kodzie, więc radar może działać w każdym województwie. Nie ma logowania ani danych osobowych. " +
      "Dane można pobrać jako CSV albo przez API JSON, a wyszukiwanie można obserwować bez konta.",
  );

  // ---- 10. Next steps and team ----
  s = pres.addSlide({ masterName: "HERO_DARK", sectionTitle: "Wartość i wdrożenie" });
  s.addImage({ data: radarImg, x: 6.2, y: 2.6, w: 4.6, h: 4.6, transparency: 55, altText: "" });
  text(s, "CO DALEJ", { x: 0.6, y: 0.4, w: 4, h: 0.3, fontSize: 12, bold: true, color: C.accent1, charSpacing: 4, valign: "middle" });
  text(s, "Od prototypu do radaru dla całej Polski", { x: 0.6, y: 0.7, w: 8.8, h: 0.6, fontSize: 30, bold: true, color: C.background1, valign: "middle" });
  const next = [
    ["Kalibracja wag", "kolejna jawna wersja kryteriów"],
    ["Wyszukiwanie semantyczne", "embeddingi obok pełnotekstowego"],
    ["Strony szkół i JST", "crawler aktualności i projektów"],
    ["Panel analityka PCI", "potwierdzanie wartości z powodem"],
    ["Kolejne źródła", "CORDIS, OpenAlex, Erasmus+"],
  ];
  s.addShape(pres.shapes.LINE, { x: 0.8, y: 1.6, w: 0, h: 3.2, line: { color: C.accent2, width: 2, transparency: 40 }, objectName: "Roadmap line" });
  next.forEach(([head, body], i) => {
    const y = 1.45 + i * 0.72;
    badge(s, i + 1, 0.62, y, C.accent2, 0.36);
    text(s, [{ text: head, options: { bold: true, color: C.background1, fontSize: 15, breakLine: true } }, { text: body, options: { color: C.background2, fontSize: 11 } }], { x: 1.15, y: y - 0.04, w: 3.4, h: 0.6 });
  });
  const team = [
    ["team-filip.jpg", "Filip Langiewicz", "filiplangiewicz"],
    ["team-mikolaj.jpg", "Mikołaj Rowicki", "mikolajrowicki"],
    ["team-maciej.jpg", "Maciej Momot", "maciej-momot"],
  ];
  text(s, "Zespół CombAIns", { x: 4.7, y: 1.5, w: 4.8, h: 0.4, fontSize: 18, bold: true, color: C.accent1, align: "center", valign: "middle" });
  team.forEach(([file, name, handle], i) => {
    const cx2 = 5.5 + i * 1.6;
    const size = 1.2;
    s.addImage({ data: glow.cyan, x: cx2 - 0.95, y: 1.85, w: 1.9, h: 1.9, altText: "" });
    s.addShape(pres.shapes.OVAL, { x: cx2 - size / 2 - 0.04, y: 2.16, w: size + 0.08, h: size + 0.08, fill: { color: C.accent1 }, line: { type: "none" }, objectName: "Photo ring" });
    s.addImage({ path: path.join(IMG, file), x: cx2 - size / 2, y: 2.2, w: size, h: size, rounding: true, altText: name });
    text(s, name, { x: cx2 - 0.78, y: 3.5, w: 1.56, h: 0.5, fontSize: 13, bold: true, color: C.background1, align: "center" });
    s.addText([{ text: `in/${handle}`, options: { hyperlink: { url: `https://www.linkedin.com/in/${handle}` } } }], { x: cx2 - 0.78, y: 3.82, w: 1.56, h: 0.25, fontSize: 9, color: C.accent1, align: "center", margin: 0, isTextBox: true });
  });
  text(s, "Dziękujemy!", { x: 4.7, y: 4.55, w: 4.8, h: 0.6, fontSize: 30, bold: true, color: C.accent2, align: "center", valign: "middle" });
  s.addNotes(
    "Po hackathonie chcemy skalibrować wagi, dodać wyszukiwanie semantyczne, czytać strony szkół i samorządów, zbudować panel analityka i dodać kolejne źródła. " +
      "Zespół CombAIns: Filip Langiewicz, Mikołaj Rowicki i Maciej Momot. Dziękujemy.",
  );

  await pres.writeFile({ fileName: OUT });
  const applyThemePath = process.argv[2];
  if (applyThemePath) {
    const { applyTheme } = require(applyThemePath);
    await applyTheme(OUT, THEME);
  }
  console.log(`Written ${OUT}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
