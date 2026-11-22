// Build the presentation for the jury: docs/presentation/Radar_innowacji.pptx.
// Needs pptxgenjs, sharp, react, react-dom and react-icons (all MIT). They are not dependencies of the application.
// Usage: NODE_PATH=<folder with node_modules> node docs/presentation/build_deck.js <path to apply_theme.js of the pptx tool>
// The screenshots in img/ come from the running application with the database of 22.11.2026.

const path = require("path");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const fa = require("react-icons/fa");

const HERE = __dirname;
const IMG = path.join(HERE, "img");
const OUT = path.join(HERE, "Radar_innowacji.pptx");

// The colors of PCI, the same as on the web page (web/style.css).
const THEME = {
  name: "Radar innowacji",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1D1D1B",
    lt1: "FFFFFF",
    dk2: "005A8C",
    lt2: "F3F7FA",
    accent1: "0072B0",
    accent2: "6BB437",
    accent3: "3A7A17",
    accent4: "8A5300",
    accent5: "0085CC",
    accent6: "4F5B67",
    hlink: "0072B0",
    folHlink: "005A8C",
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
    background: { color: C.text2 },
    objects: [
      {
        placeholder: {
          options: { name: "title", type: "title", x: 0.6, y: 1.55, w: 6.2, h: 1.1, fontSize: 48, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 },
          text: "",
        },
      },
      {
        placeholder: {
          options: { name: "body", type: "body", x: 0.6, y: 2.75, w: 5.8, h: 1.3, fontSize: 18, color: "E6F3FB", valign: "top", align: "left", margin: 0 },
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
    slideNumber: { x: 9.1, y: 5.25, w: 0.4, h: 0.25, fontSize: 9, color: "4F5B67", align: "right" },
  });

  const radar = (slide, cx, cy, r, transparency) => {
    for (const k of [1, 0.72, 0.44]) {
      slide.addShape(pres.shapes.OVAL, {
        x: cx - r * k, y: cy - r * k, w: 2 * r * k, h: 2 * r * k,
        fill: { type: "none" }, line: { color: "FFFFFF", width: 1.5, transparency }, objectName: "Radar ring",
      });
    }
    slide.addShape(pres.shapes.OVAL, { x: cx - 0.1, y: cy - 0.1, w: 0.2, h: 0.2, fill: { color: C.accent2 }, line: { type: "none" }, objectName: "Radar centre" });
  };

  const iconCircle = async (slide, Component, x, y, size, fill) => {
    slide.addShape(pres.shapes.OVAL, { x, y, w: size, h: size, fill: { color: fill }, line: { type: "none" }, objectName: "Icon circle" });
    const pad = size * 0.25;
    slide.addImage({ data: await icon(Component), x: x + pad, y: y + pad, w: size - 2 * pad, h: size - 2 * pad, altText: "" });
  };

  const shadow = () => ({ type: "outer", color: "1D1D1B", opacity: 0.16, blur: 6, offset: 2, angle: 90 });

  const screenshot = (slide, img, x, y, w, alt) => {
    const h = w / img.ratio;
    slide.addImage({ data: img.data, x, y, w, h, altText: alt, shadow: shadow() });
    slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { type: "none" }, line: { color: "DDE4EA", width: 0.75 }, objectName: "Screenshot frame" });
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

  const iconRow = async (slide, Icon, x, y, w, head, body, fill = C.accent1) => {
    await iconCircle(slide, Icon, x, y, 0.5, fill);
    slide.addText(
      [
        { text: head, options: { bold: true, fontSize: 14, color: C.text1, breakLine: true } },
        { text: body, options: { fontSize: 12, color: C.accent6 } },
      ],
      { x: x + 0.65, y: y - 0.08, w: w - 0.65, h: 0.68, valign: "top", margin: 0, isTextBox: true },
    );
  };

  const search = await crop("search", 150, 0, 1620, 1080);
  const card = await crop("card", 60, 90, 1800, 1080);
  const assessment = await crop("assessment", 0, 0, 510, 900);

  // ---- 1. Title ----
  pres.addSection({ title: "Wstęp" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Wstęp" });
  radar(s, 8.0, 2.8, 1.75, 45);
  s.addText("Radar innowacji", { placeholder: "title" });
  s.addText("Istniejące polskie innowacje w jednym miejscu: znalezione automatycznie, ocenione jawnie, gotowe do użycia.", {
    placeholder: "body",
  });
  s.addText("Zadanie Podkarpackiego Centrum Innowacji · HackNation 2026 · zespół CombAIns", {
    x: 0.6, y: 4.75, w: 7, h: 0.35, fontSize: 13, color: C.accent2, bold: true, margin: 0, isTextBox: true,
  });
  s.addNotes(
    "Radar innowacji to jedno miejsce, w którym gmina, szkoła, uczelnia, firma czy inwestor znajdzie polskie innowacje, które już działają. " +
      "Aplikacja sama je odkrywa w otwartych źródłach, ocenia według jawnych kryteriów i pokazuje, gdzie można je zastosować.",
  );

  // ---- 2. Problem ----
  pres.addSection({ title: "Problem i rozwiązanie" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem i rozwiązanie" });
  s.addText("Innowacje już istnieją, ale nikt ich nie widzi", { placeholder: "title" });
  const stats = [
    ["36 500", "projektów FE 2021–2027 w jednym arkuszu dane.gov.pl, bez wyszukiwarki rozwiązań"],
    ["19 000+", "patentów jednostek naukowych w RAD-on, opisanych językiem prawnym"],
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
      { text: "Projekty UE, patenty, strony urzędów i szkół, wyniki konkursów, zamówienia publiczne.", options: { breakLine: true } },
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

  // ---- 3. Solution: process and scale ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem i rozwiązanie" });
  s.addText("Siedem kroków od źródła do decyzji", { placeholder: "title" });
  const steps = [
    [fa.FaSearch, "Odkrywanie", "8 otwartych źródeł danych"],
    [fa.FaDatabase, "Rekord", "jeden schemat, bez danych osobowych"],
    [fa.FaTags, "Klasyfikacja", "obszar i typ innowacji"],
    [fa.FaBalanceScale, "Ocena", "5 jawnych kryteriów"],
    [fa.FaIdCard, "Karta", "dane ze źródła i przybliżenia"],
    [fa.FaFilter, "Użycie", "wyszukaj, filtruj, porównaj"],
    [fa.FaSyncAlt, "Aktualizacja", "cykliczne sprawdzanie źródeł"],
  ];
  const stepW = 1.22;
  for (const [i, [Icon, head, body]] of steps.entries()) {
    const x = 0.5 + i * (stepW + 0.075);
    await iconCircle(s, Icon, x + (stepW - 0.75) / 2, 1.3, 0.75, i === 3 ? C.accent2 : C.accent1);
    s.addText(head, { x, y: 2.2, w: stepW, h: 0.35, fontSize: 14, bold: true, color: C.text1, align: "center", margin: 0, isTextBox: true });
    s.addText(body, { x, y: 2.55, w: stepW, h: 0.6, fontSize: 11, color: C.accent6, align: "center", valign: "top", margin: 0, isTextBox: true });
    if (i < steps.length - 1) {
      s.addText("›", { x: x + stepW - 0.08, y: 1.4, w: 0.24, h: 0.5, fontSize: 24, color: "9FB3C4", align: "center", margin: 0, isTextBox: true });
    }
  }
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 3.4, w: 9, h: 1.55, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: "none" }, objectName: "Numbers" });
  const numbers = [
    ["3 498", "kart innowacji z całej Polski"],
    ["1 625", "kart z Podkarpacia"],
    ["614", "kart z poziomem wdrożenia 4–5"],
    ["< 0,2 s", "czas wyszukiwania"],
  ];
  numbers.forEach(([num, label], i) => {
    const x = 0.7 + i * 2.2;
    s.addText(num, { x, y: 3.55, w: 2.0, h: 0.65, fontSize: 30, bold: true, color: C.accent1, margin: 0, valign: "middle", isTextBox: true });
    s.addText(label, { x, y: 4.2, w: 2.0, h: 0.6, fontSize: 12, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
  });
  s.addNotes(
    "Radar sam odkrywa innowacje w ośmiu otwartych źródłach, porządkuje je w jeden schemat, klasyfikuje i ocenia. " +
      "Użytkownik niczego nie zgłasza i nie zakłada konta. Baza ma dziś 3 498 kart z całej Polski, w tym 1 625 z Podkarpacia. " +
      "Indeks powstaje z wyprzedzeniem, więc wyszukiwanie trwa ułamek sekundy, a pełna aktualizacja kilka minut.",
  );

  // ---- 4. Main flow: search ----
  pres.addSection({ title: "Demo" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
  s.addText("Wpisz potrzebę, dostaniesz istniejące rozwiązania", { placeholder: "title" });
  screenshot(s, search, 0.5, 1.15, 5.75, "Strona wyszukiwania Radaru innowacji z zapytaniem o e-usługi w urzędzie");
  numbered(s, 1, 6.6, 1.15, 2.9, "Fraza lub opis potrzeby", "np. „e-usługi w urzędzie”, „robotyka w szkole”");
  numbered(s, 2, 6.6, 2.05, 2.9, "Filtry dla 6 grup", "JST, szkoły, uczelnie, firmy, startupy, innowatorzy");
  numbered(s, 3, 6.6, 2.95, 2.9, "Ranking: trafność + potencjał", "start: Podkarpacie, szukanie: cała Polska");
  numbered(s, 4, 6.6, 4.15, 2.9, "Działa na telefonie", "wyszukiwanie, karta i porównanie");
  s.addNotes(
    "Użytkownik wpisuje frazę lub opis potrzeby. Tu: samorząd szuka e-usług w urzędzie i dostaje 156 istniejących rozwiązań. " +
      "Filtry obejmują grupę użytkowników, obszar, województwo i minimalny poziom wdrożenia. Każdy wynik pokazuje potencjał i pewność oceny.",
  );

  // ---- 5. Card ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
  s.addText("Karta innowacji: każda informacja ma źródło", { placeholder: "title" });
  numbered(s, 1, 0.5, 1.25, 3.2, "„Ze źródła” = cytat + link", "wartość pochodzi wprost ze źródła", C.accent3);
  numbered(s, 2, 0.5, 2.4, 3.2, "„Przybliżone” = powód", "wartość wyliczona regułą; powód pod „dlaczego?”", C.accent4);
  numbered(s, 3, 0.5, 3.55, 3.2, "Data sprawdzenia i licencja", "przy każdym źródle; brak danych opisany wprost");
  screenshot(s, card, 3.95, 1.15, 5.55, "Karta innowacji e-urzędu z kafelkami i panelem oceny");
  s.addNotes(
    "Karta pokazuje opis, obszar, instytucję, status wdrożenia, gotowość technologiczną i ocenę potencjału. " +
      "Każda wartość ma etykietę: „ze źródła” z cytatem i linkiem albo „przybliżone” z powodem. Przy każdym źródle jest data sprawdzenia i licencja.",
  );

  // ---- 6. Assessment ----
  pres.addSection({ title: "Ocena i dane" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ocena i dane" });
  s.addText("Jawna ocena według 5 kryteriów", { placeholder: "title" });
  s.addChart(
    pres.charts.BAR,
    [{ name: "Waga", labels: ["Wiarygodność", "Potencjał zastosowania", "Innowacyjność", "Dojrzałość (TRL)", "Poziom wdrożenia"], values: [15, 20, 20, 15, 30] }],
    {
      x: 0.4, y: 1.1, w: 5.8, h: 2.3, barDir: "bar",
      chartColors: [HEX.accent5], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: HEX.dk1,
      dataLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
      catAxisLabelFontSize: 11, catAxisLabelColor: HEX.dk1, valAxisHidden: true, valAxisMaxVal: 35,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
      showTitle: true, title: "Wagi kryteriów (suma 100)", titleFontSize: 12, titleColor: HEX.accent6, titleFontFace: "+mn-lt",
    },
  );
  s.addText(
    [
      { text: "Przedział, nie fałszywa precyzja: ", options: { bold: true } },
      { text: "brak danych to nie zero", options: { breakLine: true } },
      { text: "Pewność: ", options: { bold: true } },
      { text: "udział oceny opartej na danych ze źródła", options: { breakLine: true } },
      { text: "Potencjał zastosowania z danych: ", options: { bold: true } },
      { text: "opis, koszt, sektory, zamówienia BZP", options: { breakLine: true } },
      { text: "Powtarzalność: ", options: { bold: true } },
      { text: "ten sam rekord daje ten sam wynik; AI nie wystawia oceny", options: {} },
    ],
    { x: 0.5, y: 3.5, w: 4.8, h: 1.5, fontSize: 13, color: C.text1, valign: "top", margin: 0, paraSpaceAfter: 4, isTextBox: true },
  );
  const ah = 3.8;
  s.addImage({ data: assessment.data, x: 7.15, y: 1.05, w: ah * assessment.ratio, h: ah, altText: "Panel oceny na karcie wynalazku z kryteriami jako paski", shadow: shadow() });
  s.addText("Skale: TRL (Komisja Europejska), Oslo Manual 2018, Nesta, Interreg Europe.", {
    x: 0.5, y: 4.98, w: 9, h: 0.25, fontSize: 9, color: C.accent6, margin: 0, align: "right", isTextBox: true,
  });
  s.addNotes(
    "Pięć kryteriów: poziom wdrożenia, dojrzałość technologiczna, innowacyjność, potencjał zastosowania i wiarygodność. Wagi to jawna propozycja zespołu w wersji v0.1. " +
      "Brak danych nie oznacza zera, więc pokazujemy przedział. Potencjał zastosowania liczymy z danych: opisu, kosztu, liczby sektorów i zamówień publicznych. " +
      "Model językowy może proponować wartości, ale nigdy nie jest jedynym źródłem oceny.",
  );

  // ---- 7. Sources ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ocena i dane" });
  s.addText("8 otwartych źródeł i zamówienia publiczne", { placeholder: "title" });
  const sources = [
    [fa.FaEuroSign, "Lista projektów FE 2021–2027", "967 kart", "CC0 1.0"],
    [fa.FaUniversity, "RAD-on (OPI PIB)", "927 kart: patenty i projekty", "CC0 1.0"],
    [fa.FaCertificate, "EPO Linked Open Data", "1 164 patenty europejskie", "CC BY 4.0"],
    [fa.FaTrophy, "NCBR: sukcesy beneficjentów", "300 kart", "opis + link"],
    [fa.FaGlobeEurope, "Kohesio (KE), projekty 2014–2020", "56 kart", "zasady KE"],
    [fa.FaHandshake, "Interreg 2021–2027", "50 kart", "CC0 1.0"],
    [fa.FaLandmark, "Konkurs „Innowacyjny Samorząd”", "42 karty", "cytat + link"],
    [fa.FaShoppingCart, "Zamówienia publiczne (BZP)", "2 803 ogłoszenia: sygnał popytu", "informacja publiczna"],
  ];
  for (const [i, [Icon, head, body, lic]] of sources.entries()) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * 4.6;
    const y = 1.15 + row * 0.86;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 4.4, h: 0.76, rectRadius: 0.08, fill: { color: C.background2 }, line: { type: "none" }, objectName: `Source ${i + 1}` });
    await iconCircle(s, Icon, x + 0.15, y + 0.13, 0.5, i === 7 ? C.accent2 : C.accent1);
    s.addText(
      [
        { text: head, options: { bold: true, fontSize: 13, color: C.text1, breakLine: true } },
        { text: `${body} · `, options: { fontSize: 11, color: C.accent6 } },
        { text: lic, options: { fontSize: 11, color: C.accent3, bold: true } },
      ],
      { x: x + 0.8, y: y + 0.06, w: 3.5, h: 0.64, valign: "middle", margin: 0, isTextBox: true },
    );
  }
  s.addText("Każdy rekord ma źródło, datę danych, datę pobrania i licencję. Awaria jednego źródła nie zatrzymuje pozostałych.", {
    x: 0.5, y: 4.65, w: 9, h: 0.4, fontSize: 13, color: C.text1, margin: 0, valign: "middle", isTextBox: true,
  });
  s.addNotes(
    "Korzystamy tylko z bezpłatnych i legalnych źródeł, bez kluczy API. Każdy rekord ma licencję i datę sprawdzenia. " +
      "Rekordy z różnych źródeł o tej samej innowacji łączymy w jedną kartę z osią czasu. Nie pobieramy danych osób: oceniamy innowację, nie człowieka.",
  );

  // ---- 8. Two use cases: where to apply, who can use it, the next path and its measures ----
  pres.addSection({ title: "Przypadki użycia" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Przypadki użycia" });
  s.addText("Dwa przypadki: gdzie zastosować i co dalej", { placeholder: "title" });
  const useCase = async (x, Icon, fill, head, lines) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.1, w: 4.4, h: 3.95, rectRadius: 0.1, fill: { color: C.background2 }, line: { type: "none" }, objectName: head });
    await iconCircle(s, Icon, x + 0.2, 1.22, 0.5, fill);
    s.addText(head, { x: x + 0.82, y: 1.22, w: 3.45, h: 0.5, fontSize: 15, bold: true, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
    s.addText(
      lines.flatMap(([label, text], i) => [
        { text: `${label}: `, options: { bold: true, color: C.text1 } },
        { text, options: { color: C.text1, breakLine: i < lines.length - 1 } },
      ]),
      { x: x + 0.22, y: 1.85, w: 4.0, h: 3.1, fontSize: 13, valign: "top", margin: 0, paraSpaceAfter: 4, isTextBox: true },
    );
  };
  await useCase(0.5, fa.FaLandmark, C.accent1, "Samorząd szuka e-usług", [
    ["Zapytanie", "„e-usługi w urzędzie”, grupa JST"],
    ["Karta", "e-urząd w Gminie Horyniec-Zdrój: wdrożenie pilotażowe, ocena 69 (53–76)"],
    ["Gdzie zastosować", "administracja publiczna; ICT i cyfryzacja"],
    ["Ścieżka", "replikacja w innej instytucji"],
    ["Mierniki", "instytucje, które przejęły rozwiązanie w 12 mies.; użytkownicy; czas obsługi sprawy"],
    ["Podobne wdrożenia", "Cieszanów, Krasiczyn, Stubno, Dydnia"],
    ["Popyt (BZP)", "Biłgoraj, Wadowice, Dąbrowa Tarnowska"],
  ]);
  await useCase(5.1, fa.FaFlask, C.accent3, "Technologia z uczelni", [
    ["Zapytanie", "„elektroda zgrzewanie”"],
    ["Karta", "bezodpadowa technologia elektrod nasadkowych, Politechnika Rzeszowska: prototyp, ocena 43 (28–63)"],
    ["Dwa źródła w jednej karcie", "grant 2017 → zgłoszenie 2022 → prawo ochronne 2025; wiarygodność 4/5"],
    ["Ścieżka", "transfer technologii: licencja lub wspólny projekt B+R"],
    ["Mierniki", "zapytania od firm; umowa licencyjna lub B+R w 12 mies.; wzrost TRL o co najmniej 1"],
  ]);

  s.addNotes(
    "Dwa przypadki z prawdziwych danych. Gmina szuka e-usług: radar pokazuje e-urząd w Horyńcu-Zdroju, gminy z podobnym wdrożeniem i instytucje, które kupują podobne rozwiązania. " +
      "Rekomendowana ścieżka to replikacja w innej instytucji, z miernikami skuteczności. " +
      "Drugi przypadek: technologia Politechniki Rzeszowskiej. Radar łączy projekt badawczy i patent w jedną kartę z osią czasu i proponuje transfer technologii.",
  );

  // ---- 9. Decision tool and deployment ----
  pres.addSection({ title: "Wartość i wdrożenie" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Wartość i wdrożenie" });
  s.addText("Narzędzie do decyzji, gotowe do wdrożenia", { placeholder: "title" });
  s.addText("Dla użytkownika", { x: 0.5, y: 1.05, w: 4.3, h: 0.35, fontSize: 15, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText("Dla PCI i innych organizacji", { x: 5.2, y: 1.05, w: 4.3, h: 0.35, fontSize: 15, bold: true, color: C.accent3, margin: 0, isTextBox: true });
  const userFeatures = [
    [fa.FaColumns, "Porównanie 2–4 kart", "kryteria w wierszach, link do udostępnienia"],
    [fa.FaBell, "Obserwowane wyszukiwania", "„Nowe od ostatniej wizyty”, bez logowania"],
    [fa.FaStream, "Oś czasu z kilku źródeł", "grant, patent, nagroda, wdrożenie"],
    [fa.FaFileCsv, "Eksport CSV i API JSON", "dane do arkusza, CRM lub innego systemu"],
    [fa.FaChartBar, "Anonimowa analityka", "popularne obszary, bez danych o osobach"],
  ];
  const orgFeatures = [
    [fa.FaMapMarkedAlt, "Region w konfiguracji", "inne centrum uruchamia radar bez zmian w kodzie"],
    [fa.FaPuzzlePiece, "Jedno źródło = jeden moduł", "nowe źródło to jedna funkcja"],
    [fa.FaServer, "Lekka infrastruktura", "SQLite, zwykły serwer, bez GPU i opłat"],
    [fa.FaLock, "Bezpieczeństwo", "bez logowania; dane osób ukryte; AI Act"],
    [fa.FaBalanceScaleLeft, "Licencja EUPL-1.2", "tylko komponenty z otwartymi licencjami"],
  ];
  for (const [i, [Icon, head, body]] of userFeatures.entries()) await iconRow(s, Icon, 0.5, 1.55 + i * 0.72, 4.4, head, body, C.accent1);
  for (const [i, [Icon, head, body]] of orgFeatures.entries()) await iconRow(s, Icon, 5.2, 1.55 + i * 0.72, 4.3, head, body, C.accent3);
  s.addNotes(
    "Radar nie kończy się na liście: można porównać karty, obserwować wyszukiwania, wyeksportować dane do CSV i pobrać je przez API. " +
      "Region i źródła są w konfiguracji, a nie w kodzie, więc radar może działać w każdym województwie. Nie ma logowania ani danych osobowych. " +
      "Fundusze VC budują własne platformy danych do szukania projektów, np. EQT Motherbrain. PFR Ventures w programie Starter Science ocenia, czy fundusze umieją znaleźć projekty z nauki. Radar daje tę metodę PCI, samorządom i uczelniom.",
  );

  // ---- 10. Next steps ----
  s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Wartość i wdrożenie" });
  radar(s, 8.4, 4.4, 1.5, 55);
  s.addText("Co dalej", { x: 0.6, y: 0.45, w: 6, h: 0.7, fontSize: 32, bold: true, color: C.background1, margin: 0, isTextBox: true });
  const next = [
    ["Kalibracja wag", ""],
    ["Wyszukiwanie semantyczne", "embeddingi obok wyszukiwania pełnotekstowego"],
    ["Strony szkół i JST", "crawler aktualności i projektów"],
    ["Panel analityka PCI", "potwierdzanie wartości z zapisem powodu"],
    ["Kolejne źródła", "CORDIS, OpenAlex, wyniki Erasmus+"],
  ];
  next.forEach(([head, body], i) => {
    const y = 1.35 + i * 0.65;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y: y + 0.05, w: 0.4, h: 0.4, fill: { color: C.accent2 }, line: { type: "none" }, objectName: `Next ${i + 1}` });
    s.addText(String(i + 1), { x: 0.6, y: y + 0.05, w: 0.4, h: 0.4, fontSize: 14, bold: true, color: C.text1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(
      [
        { text: `${head}  `, options: { bold: true, color: C.background1 } },
        { text: body, options: { color: "E6F3FB" } },
      ],
      { x: 1.2, y, w: 5.8, h: 0.5, fontSize: 16, valign: "middle", margin: 0, isTextBox: true },
    );
  });
  s.addText("Zespół CombAIns: Filip Langiewicz, Maciej Momot, Mikołaj Rowicki", {
    x: 0.6, y: 4.8, w: 6, h: 0.4, fontSize: 14, bold: true, color: C.accent2, margin: 0, isTextBox: true,
  });
  s.addNotes(
    "Po hackathonie chcemy skalibrować wagi, dodać wyszukiwanie semantyczne, czytać strony szkół i samorządów, zbudować panel analityka i dodać kolejne źródła. Dziękujemy.",
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
