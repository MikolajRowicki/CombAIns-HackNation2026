// Build the presentation for the jury: docs/presentation/Radar_innowacji.pptx.
// Needs pptxgenjs, sharp, react, react-dom and react-icons (all MIT). They are not dependencies of the application.
// Usage: NODE_PATH=<folder with node_modules> node docs/presentation/build_deck.js <path to apply_theme.js of the pptx tool>
// The screenshots in img/ come from the running application (search, card, assessment, comparison).

const path = require("path");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const fa = require("react-icons/fa");

const HERE = __dirname;
const IMG = path.join(HERE, "img");
const OUT = path.join(HERE, "Radar_innowacji.pptx");

// The colors of the web page (web/style.css), so that the slides and the application look the same.
const THEME = {
  name: "Radar innowacji",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "17212F",
    lt1: "FFFFFF",
    dk2: "2B3A4F",
    lt2: "F3F5F8",
    accent1: "0A58A8",
    accent2: "F2A900",
    accent3: "1D7A46",
    accent4: "6B3FA0",
    accent5: "8A4B0F",
    accent6: "5B6675",
    hlink: "0A58A8",
    folHlink: "6B3FA0",
  },
};
const HEX = THEME.colors;

async function icon(Component, color = "FFFFFF") {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Component, { color: `#${color}`, size: 256 }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

async function crop(name, left, top, width, height) {
  const buf = await sharp(path.join(IMG, `${name}.png`)).extract({ left, top, width, height }).png().toBuffer();
  return { data: "image/png;base64," + buf.toString("base64"), ratio: width / height };
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
  pres.title = "Radar innowacji";
  pres.subject = "Zadanie PCI, HackNation 2026";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // ---- Layouts ----
  pres.defineSlideMaster({
    title: "TITLE_DARK",
    background: { color: C.text1 },
    objects: [
      {
        placeholder: {
          options: { name: "title", type: "title", x: 0.6, y: 1.55, w: 6.2, h: 1.1, fontSize: 48, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 },
          text: "",
        },
      },
      {
        placeholder: {
          options: { name: "body", type: "body", x: 0.6, y: 2.75, w: 5.8, h: 1.3, fontSize: 18, color: "D5DCE6", valign: "top", align: "left", margin: 0 },
          text: "",
        },
      },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: C.background1 },
    objects: [
      {
        placeholder: {
          options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.65, fontSize: 28, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 },
          text: "",
        },
      },
      { text: { text: "Radar innowacji · HackNation 2026", options: { x: 0.5, y: 5.25, w: 4, h: 0.25, fontSize: 9, color: C.accent6, margin: 0 } } },
    ],
    slideNumber: { x: 9.1, y: 5.25, w: 0.4, h: 0.25, fontSize: 9, color: "5B6675", align: "right" },
  });

  const radar = (slide, cx, cy, r, color, transparency) => {
    for (const k of [1, 0.72, 0.44]) {
      slide.addShape(pres.shapes.OVAL, {
        x: cx - r * k, y: cy - r * k, w: 2 * r * k, h: 2 * r * k,
        fill: { type: "none" }, line: { color, width: 1.5, transparency }, objectName: "Radar ring",
      });
    }
    slide.addShape(pres.shapes.OVAL, { x: cx - 0.09, y: cy - 0.09, w: 0.18, h: 0.18, fill: { color: C.accent2 }, line: { type: "none" }, objectName: "Radar centre" });
  };

  const iconCircle = async (slide, Component, x, y, size, fill) => {
    slide.addShape(pres.shapes.OVAL, { x, y, w: size, h: size, fill: { color: fill }, line: { type: "none" }, objectName: "Icon circle" });
    const pad = size * 0.25;
    slide.addImage({ data: await icon(Component), x: x + pad, y: y + pad, w: size - 2 * pad, h: size - 2 * pad, altText: "" });
  };

  const shadow = () => ({ type: "outer", color: "17212F", opacity: 0.18, blur: 6, offset: 2, angle: 90 });

  const screenshot = (slide, img, x, y, w, alt) => {
    const h = w / img.ratio;
    slide.addImage({ data: img.data, x, y, w, h, altText: alt, shadow: shadow() });
    slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { type: "none" }, line: { color: "D6DCE4", width: 0.75 }, objectName: "Screenshot frame" });
    return h;
  };

  const numbered = (slide, n, x, y, w, head, body, color = C.accent1) => {
    slide.addShape(pres.shapes.OVAL, { x, y, w: 0.42, h: 0.42, fill: { color }, line: { type: "none" }, objectName: `Step ${n}` });
    slide.addText(String(n), { x, y, w: 0.42, h: 0.42, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    slide.addText(
      [
        { text: head, options: { bold: true, fontSize: 15, color: C.text1, breakLine: true } },
        { text: body, options: { fontSize: 13, color: C.accent6 } },
      ],
      { x: x + 0.58, y: y - 0.04, w: w - 0.58, h: 0.95, valign: "top", margin: 0, isTextBox: true, paraSpaceAfter: 2 },
    );
  };

  const search = await crop("search", 240, 0, 1440, 950);
  const card = await crop("card", 240, 0, 1440, 950);
  const assessment = await crop("assessment", 280, 40, 1380, 1000);
  const compare = await crop("compare", 0, 230, 1250, 900);

  // ---- 1. Title ----
  pres.addSection({ title: "Wstęp" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Wstęp" });
  radar(s, 8.0, 2.8, 1.75, C.accent2, 40);
  s.addText("Radar innowacji", { placeholder: "title" });
  s.addText("Istniejące polskie innowacje w jednym miejscu: znalezione automatycznie, ocenione jawnie, gotowe do użycia.", {
    placeholder: "body",
  });
  s.addText("Zadanie Podkarpackiego Centrum Innowacji · HackNation 2026 · zespół CombAIns", {
    x: 0.6, y: 4.75, w: 7, h: 0.35, fontSize: 13, color: C.accent2, margin: 0, isTextBox: true,
  });
  s.addNotes(
    "Radar innowacji to jedno miejsce, w którym gmina, szkoła, uczelnia, firma czy inwestor znajdzie polskie innowacje, które już działają. " +
      "Aplikacja sama je odkrywa w otwartych źródłach, ocenia według jawnych kryteriów z FAQ i pokazuje, gdzie można je zastosować.",
  );

  // ---- 2. Problem ----
  pres.addSection({ title: "Problem i rozwiązanie" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem i rozwiązanie" });
  s.addText("Innowacje już istnieją, ale nikt ich nie widzi", { placeholder: "title" });
  const stats = [
    ["36 500", "projektów FE 2021–2027 w jednym arkuszu dane.gov.pl, bez wyszukiwarki rozwiązań"],
    ["19 032", "patenty jednostek naukowych w RAD-on, opisane językiem prawnym"],
    ["~10%", "inwestycji funduszy VC z udziałem środków UE ma komponent naukowy (2019–2026)"],
  ];
  stats.forEach(([num, label], i) => {
    const y = 1.2 + i * 1.3;
    s.addText(num, { x: 0.5, y, w: 2.3, h: 0.75, fontSize: 40, bold: true, color: C.accent1, margin: 0, valign: "middle", isTextBox: true });
    s.addText(label, { x: 2.9, y: y + 0.05, w: 2.6, h: 0.7, fontSize: 12, color: C.accent6, margin: 0, valign: "middle", isTextBox: true });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.9, y: 1.2, w: 3.6, h: 3.75, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: "none" }, objectName: "Problem card" });
  s.addText(
    [
      { text: "Informacje są rozproszone", options: { bold: true, breakLine: true } },
      { text: "Projekty UE, patenty, strony urzędów i szkół, wyniki konkursów, media lokalne.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Katalogi wymagają zgłoszeń", options: { bold: true, breakLine: true } },
      { text: "Obejmują jeden sektor i szybko się dezaktualizują.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Skutek", options: { bold: true, breakLine: true } },
      { text: "Gmina nie wie, że inna gmina już rozwiązała ten sam problem.", options: {} },
    ],
    { x: 6.15, y: 1.4, w: 3.15, h: 3.4, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true },
  );
  s.addText("Źródła: dane.gov.pl, RAD-on (OPI PIB), xyz.pl na podstawie danych PFR Ventures.", {
    x: 0.5, y: 4.95, w: 5.2, h: 0.25, fontSize: 9, color: C.accent6, margin: 0, isTextBox: true,
  });
  s.addNotes(
    "Dane o innowacjach istnieją, ale są rozproszone. Lista projektów FE to 36,5 tys. wierszy w jednym pliku. RAD-on ma ponad 19 tys. patentów uczelni. " +
      "Tylko około 10% inwestycji funduszy VC finansowanych ze środków UE ma komponent naukowy. Katalogi dobrych praktyk wymagają ręcznego zgłaszania.",
  );

  // ---- 3. Solution: process ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem i rozwiązanie" });
  s.addText("Siedem kroków od źródła do decyzji", { placeholder: "title" });
  const steps = [
    [fa.FaSearch, "Odkrywanie", "API, zbiory danych, strony WWW"],
    [fa.FaDatabase, "Rekord", "jeden schemat, bez danych osobowych"],
    [fa.FaTags, "Klasyfikacja", "obszar i typ innowacji"],
    [fa.FaBalanceScale, "Ocena", "5 kryteriów z FAQ"],
    [fa.FaIdCard, "Karta", "fakty, szacunki, źródła"],
    [fa.FaFilter, "Użycie", "wyszukaj, filtruj, porównaj"],
    [fa.FaSyncAlt, "Aktualizacja", "cykliczne sprawdzanie źródeł"],
  ];
  const stepW = 1.22;
  for (const [i, [Icon, head, body]] of steps.entries()) {
    const x = 0.5 + i * (stepW + 0.075);
    await iconCircle(s, Icon, x + (stepW - 0.75) / 2, 1.35, 0.75, i === 3 ? C.accent2 : C.accent1);
    s.addText(head, { x, y: 2.25, w: stepW, h: 0.35, fontSize: 14, bold: true, color: C.text1, align: "center", margin: 0, isTextBox: true });
    s.addText(body, { x, y: 2.6, w: stepW, h: 0.6, fontSize: 11, color: C.accent6, align: "center", valign: "top", margin: 0, isTextBox: true });
    if (i < steps.length - 1) {
      s.addText("›", { x: x + stepW - 0.08, y: 1.45, w: 0.24, h: 0.5, fontSize: 24, color: "B8C2CE", align: "center", margin: 0, isTextBox: true });
    }
  }
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 3.55, w: 9, h: 1.35, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: "none" }, objectName: "Principles" });
  const principles = [
    ["Bez ręcznego zgłaszania", "radar sam znajduje innowacje w otwartych źródłach"],
    ["Bez logowania i klucza API", "każdy wyszukuje i czyta karty od razu"],
    ["Indeks budowany z wyprzedzeniem", "wynik w kilka sekund, także gdy źródło nie działa"],
  ];
  principles.forEach(([head, body], i) => {
    s.addText(
      [
        { text: head, options: { bold: true, fontSize: 15, color: C.text1, breakLine: true } },
        { text: body, options: { fontSize: 13, color: C.accent6 } },
      ],
      { x: 0.75 + i * 2.95, y: 3.7, w: 2.75, h: 1.05, valign: "middle", margin: 0, isTextBox: true },
    );
  });
  s.addNotes(
    "Proces odpowiada sekcji 8 FAQ: odkrywanie, rekord, klasyfikacja, ocena, karta, użycie i aktualizacja. " +
      "Użytkownik niczego nie zgłasza i nie zakłada konta. Indeks powstaje z wyprzedzeniem, więc wyszukiwanie działa szybko nawet przy awarii źródła.",
  );

  // ---- 4. Main flow: search ----
  pres.addSection({ title: "Demo" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
  s.addText("Wpisz potrzebę, dostaniesz istniejące rozwiązania", { placeholder: "title" });
  screenshot(s, search, 0.5, 1.15, 5.75, "Strona wyszukiwania Radaru innowacji z filtrami i listą wyników");
  numbered(s, 1, 6.6, 1.25, 2.9, "Fraza lub opis potrzeby", "np. „e-usługi w urzędzie”, „robotyka w szkole”");
  numbered(s, 2, 6.6, 2.4, 2.9, "Filtry dla 6 grup z FAQ", "JST, szkoły, uczelnie, firmy i inwestorzy, startupy, innowatorzy");
  numbered(s, 3, 6.6, 3.55, 2.9, "Ranking: trafność + potencjał", "70% trafności, 30% oceny; start: Podkarpacie, szukanie: cała Polska");
  s.addNotes(
    "Główny przepływ: użytkownik wpisuje frazę lub opis potrzeby i dostaje listę istniejących innowacji. " +
      "Filtry obejmują grupę użytkowników, obszar, województwo i minimalny poziom wdrożenia. Każdy wynik pokazuje potencjał i pewność oceny.",
  );

  // ---- 5. Card ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
  s.addText("Karta innowacji: każda informacja ma źródło", { placeholder: "title" });
  numbered(s, 1, 0.5, 1.25, 3.2, "„Fakt” = cytat + link", "wartość pochodzi wprost ze źródła", C.accent3);
  numbered(s, 2, 0.5, 2.4, 3.2, "„Szacunek” = etykieta + powód", "wartość oszacowana regułą, z uzasadnieniem", C.accent4);
  numbered(s, 3, 0.5, 3.55, 3.2, "Data sprawdzenia i licencja", "przy każdym źródle; brak danych opisany wprost");
  screenshot(s, card, 3.95, 1.15, 5.55, "Karta innowacji z oznaczeniami fakt i szacunek");
  s.addNotes(
    "Karta ma wszystkie elementy z sekcji 5 FAQ: opis, obszar, źródło, status wdrożenia, poziom gotowości i ocenę potencjału. " +
      "Oddzielamy fakty od szacunków: fakt ma cytat i link, szacunek ma etykietę i powód. Pokazujemy datę sprawdzenia i licencję każdego źródła.",
  );

  // ---- 6. Assessment ----
  pres.addSection({ title: "Ocena i dane" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ocena i dane" });
  s.addText("Jawna ocena według 5 kryteriów z FAQ", { placeholder: "title" });
  s.addChart(
    pres.charts.BAR,
    [{ name: "Waga", labels: ["K5 Wiarygodność", "K4 Potencjał zastosowania", "K3 Innowacyjność", "K2 Dojrzałość (TRL)", "K1 Poziom wdrożenia"], values: [15, 20, 20, 15, 30] }],
    {
      x: 0.4, y: 1.1, w: 4.4, h: 2.35, barDir: "bar",
      chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: HEX.dk1,
      dataLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
      catAxisLabelFontSize: 11, catAxisLabelColor: HEX.dk1, valAxisHidden: true, valAxisMaxVal: 35,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
      showTitle: true, title: "Wagi kryteriów (v0.1, suma 100)", titleFontSize: 12, titleColor: HEX.accent6, titleFontFace: "+mn-lt",
    },
  );
  s.addText(
    [
      { text: "Przedział, nie fałszywa precyzja: ", options: { bold: true } },
      { text: "brak danych to nie zero", options: { breakLine: true } },
      { text: "Pewność: ", options: { bold: true } },
      { text: "udział wagi opartej na faktach", options: { breakLine: true } },
      { text: "Powtarzalność: ", options: { bold: true } },
      { text: "wersja kryteriów przy każdej ocenie", options: { breakLine: true } },
      { text: "AI może proponować wartość, ", options: { bold: true } },
      { text: "ale nie wystawia oceny", options: {} },
    ],
    { x: 0.5, y: 3.55, w: 4.3, h: 1.45, fontSize: 13, color: C.text1, valign: "top", margin: 0, paraSpaceAfter: 4, isTextBox: true },
  );
  screenshot(s, assessment, 5.05, 1.15, 4.45, "Tabela oceny na karcie innowacji z wagami, punktami i uzasadnieniem");
  s.addText("Wagi: propozycja zespołu do kalibracji z mentorami PCI. Skale: TRL (KE), Oslo Manual 2018, Nesta, Interreg Europe.", {
    x: 5.05, y: 4.5, w: 4.45, h: 0.5, fontSize: 10, color: C.accent6, margin: 0, valign: "top", isTextBox: true,
  });
  s.addNotes(
    "Kryteria pochodzą z FAQ: poziom wdrożenia, TRL, innowacyjność, potencjał zastosowania i wiarygodność. Wagi to nasza propozycja v0.1. " +
      "Brak danych nie oznacza zera, więc pokazujemy przedział. Pewność zależy od tego, ile wagi opiera się na faktach. Ten sam rekord zawsze daje ten sam wynik.",
  );

  // ---- 7. Sources ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ocena i dane" });
  s.addText("Tylko otwarte, legalne źródła z całej Polski", { placeholder: "title" });
  const sources = [
    [fa.FaEuroSign, "Lista projektów FE 2021–2027", "ok. 36 500 projektów z opisem, beneficjentem i lokalizacją", "CC0 1.0"],
    [fa.FaUniversity, "RAD-on (OPI PIB)", "patenty jednostek naukowych i projekty badawcze", "CC0 1.0"],
    [fa.FaGlobe, "Strony instytucji i konkursów", "JST, szkoły, uczelnie, laureaci konkursów; robots.txt", "streszczenie + link"],
    [fa.FaShoppingCart, "Zamówienia publiczne (BZP)", "kto kupuje podobne rozwiązania: sygnał popytu", "dane publiczne"],
  ];
  for (const [i, [Icon, head, body, lic]] of sources.entries()) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * 4.6;
    const y = 1.2 + row * 1.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 4.4, h: 1.4, rectRadius: 0.1, fill: { color: C.background2 }, line: { type: "none" }, objectName: `Source ${i + 1}` });
    await iconCircle(s, Icon, x + 0.25, y + 0.3, 0.75, C.accent1);
    s.addText(
      [
        { text: head, options: { bold: true, fontSize: 15, color: C.text1, breakLine: true } },
        { text: body, options: { fontSize: 13, color: C.accent6, breakLine: true } },
        { text: `Licencja: ${lic}`, options: { fontSize: 11, color: C.accent3, bold: true } },
      ],
      { x: x + 1.2, y: y + 0.12, w: 3.05, h: 1.16, valign: "middle", margin: 0, isTextBox: true },
    );
  }
  s.addText("Każdy rekord ma źródło, datę danych, datę pobrania i licencję. Awaria jednego źródła nie zatrzymuje pozostałych.", {
    x: 0.5, y: 4.45, w: 9, h: 0.45, fontSize: 14, color: C.text1, margin: 0, valign: "middle", isTextBox: true,
  });
  s.addNotes(
    "Korzystamy tylko z bezpłatnych i legalnych źródeł, bez kluczy API. Każdy rekord ma zapisaną licencję i datę sprawdzenia. " +
      "Ze stron WWW zapisujemy tylko krótkie streszczenie i link. Nie pobieramy danych osobowych: oceniamy innowację, nie człowieka.",
  );

  // ---- 8. Differentiators ----
  pres.addSection({ title: "Wartość i wdrożenie" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Wartość i wdrożenie" });
  s.addText("Więcej niż katalog: narzędzie do decyzji", { placeholder: "title" });
  const diffs = [
    [fa.FaColumns, "Porównanie 2–4 kart", "kryteria w wierszach, link do udostępnienia"],
    [fa.FaBell, "Obserwowane wyszukiwania", "„Nowe od ostatniej wizyty”, bez logowania"],
    [fa.FaShoppingCart, "Sygnały popytu", "instytucje, które kupują podobne rozwiązania"],
    [fa.FaStream, "Oś czasu sygnałów", "patent, grant, nagroda, wdrożenie"],
  ];
  for (const [i, [Icon, head, body]] of diffs.entries()) {
    const y = 1.2 + i * 0.95;
    await iconCircle(s, Icon, 0.5, y, 0.62, i < 2 ? C.accent1 : C.accent3);
    s.addText(
      [
        { text: head, options: { bold: true, fontSize: 15, color: C.text1, breakLine: true } },
        { text: body, options: { fontSize: 13, color: C.accent6 } },
      ],
      { x: 1.3, y: y - 0.08, w: 3.2, h: 0.8, valign: "middle", margin: 0, isTextBox: true },
    );
  }
  const compareH = screenshot(s, compare, 4.75, 1.2, 4.75, "Tabela porównania trzech innowacji według kryteriów");
  s.addText("Porównanie innowacji z różnych obszarów i regionów w jednej tabeli.", {
    x: 4.75, y: 1.3 + compareH, w: 4.75, h: 0.35, fontSize: 11, color: C.accent6, margin: 0, isTextBox: true,
  });
  s.addNotes(
    "Radar nie kończy się na liście. Użytkownik porównuje 2–4 innowacje w tabeli kryteriów, zapisuje wyszukiwania i widzi nowe wyniki po aktualizacji. " +
      "Karta pokazuje też instytucje, które kupują podobne rozwiązania, oraz oś czasu sygnałów: tę samą metodę stosują fundusze VC.",
  );

  // ---- 9. Scale-up ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Wartość i wdrożenie" });
  s.addText("Gotowe do wdrożenia w PCI i w całej Polsce", { placeholder: "title" });
  const scale = [
    [fa.FaMapMarkedAlt, "Region w konfiguracji", "inne centrum uruchamia radar bez zmian w kodzie"],
    [fa.FaPuzzlePiece, "Jedno źródło = jeden moduł", "nowe źródło to jedna funkcja"],
    [fa.FaServer, "Lekka infrastruktura", "SQLite, zwykły serwer, bez GPU i opłat"],
    [fa.FaPlug, "Integracja", "otwarte API JSON i eksport CSV"],
    [fa.FaLock, "Bezpieczeństwo", "bez logowania i danych osobowych; AI Act"],
    [fa.FaBalanceScaleLeft, "Licencja EUPL-1.2", "tylko komponenty z otwartymi licencjami"],
  ];
  for (const [i, [Icon, head, body]] of scale.entries()) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * 3.05;
    const y = 1.2 + row * 1.15;
    await iconCircle(s, Icon, x, y, 0.55, C.accent1);
    s.addText(
      [
        { text: head, options: { bold: true, fontSize: 14, color: C.text1, breakLine: true } },
        { text: body, options: { fontSize: 12, color: C.accent6 } },
      ],
      { x: x + 0.7, y: y - 0.1, w: 2.2, h: 0.95, valign: "top", margin: 0, isTextBox: true },
    );
  }
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.75, y: 1.2, w: 2.75, h: 3.3, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: "none" }, objectName: "Pitch card" });
  s.addText(
    [
      { text: "Dlaczego teraz", options: { bold: true, fontSize: 16, color: C.accent2, breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "PFR Ventures uruchamia „Starter Science” i ocenia, czy fundusze umieją znaleźć projekty z nauki.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "EQT Motherbrain: własna platforma danych znalazła 7 z ok. 50 inwestycji EQT Ventures.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Radar daje tę metodę PCI i JST, na danych publicznych.", options: { bold: true } },
    ],
    { x: 6.95, y: 1.4, w: 2.4, h: 2.95, fontSize: 13, color: C.background1, valign: "top", margin: 0, isTextBox: true },
  );
  s.addNotes(
    "Radar nie ma na stałe wpisanego regionu: region i lista stron są w konfiguracji. Każde źródło to osobny moduł. " +
      "Działa na zwykłym serwerze, udostępnia API i CSV. Nie ma logowania ani danych osobowych. " +
      "Fundusze VC budują własne platformy danych do szukania projektów. Radar daje tę metodę PCI, samorządom i uczelniom.",
  );

  // ---- 10. Next steps ----
  s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Wartość i wdrożenie" });
  radar(s, 8.4, 4.4, 1.5, C.accent2, 55);
  s.addText("Co dalej", { x: 0.6, y: 0.45, w: 6, h: 0.7, fontSize: 32, bold: true, color: C.background1, margin: 0, isTextBox: true });
  const next = [
    ["Kalibracja wag", "z mentorami i analitykami PCI"],
    ["Więcej źródeł", "Kohesio, UPRP, Interreg, CORDIS, OpenAlex"],
    ["Panel analityka", "potwierdzanie wartości z zapisem powodu"],
    ["Powiadomienia e-mail", "nowe karty dla obserwowanych wyszukiwań"],
  ];
  next.forEach(([head, body], i) => {
    const y = 1.4 + i * 0.75;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y: y + 0.05, w: 0.4, h: 0.4, fill: { color: C.accent2 }, line: { type: "none" }, objectName: `Next ${i + 1}` });
    s.addText(String(i + 1), { x: 0.6, y: y + 0.05, w: 0.4, h: 0.4, fontSize: 14, bold: true, color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(
      [
        { text: `${head}  `, options: { bold: true, color: C.background1 } },
        { text: body, options: { color: "D5DCE6" } },
      ],
      { x: 1.2, y, w: 5.6, h: 0.5, fontSize: 16, valign: "middle", margin: 0, isTextBox: true },
    );
  });
  s.addText("Zespół CombAIns: Maciej Momot, Mikołaj Rowicki", {
    x: 0.6, y: 4.65, w: 6, h: 0.4, fontSize: 14, color: C.accent2, margin: 0, isTextBox: true,
  });
  s.addNotes(
    "Po hackathonie chcemy skalibrować wagi z PCI, dodać kolejne źródła, panel dla analityka i powiadomienia e-mail. Dziękujemy.",
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
