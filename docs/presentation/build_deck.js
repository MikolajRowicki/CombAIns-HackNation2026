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
    ],
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

  const shadow = () => ({ type: "outer", color: "1D1D1B", opacity: 0.16, blur: 6, offset: 2, angle: 90 });

  const screenshot = (slide, img, x, y, w, alt) => {
    const h = w / img.ratio;
    slide.addImage({ data: img.data, x, y, w, h, altText: alt, shadow: shadow() });
    slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { type: "none" }, line: { color: "DDE4EA", width: 0.75 }, objectName: "Screenshot frame" });
    return h;
  };

  // A list of "head – body" items as text only.
  const items = (slide, list, x, y, w, h, size = 13) => {
    slide.addText(
      list.flatMap(([head, body], i) => [
        { text: head, options: { bold: true, color: C.text1 } },
        { text: body ? ` – ${body}` : "", options: { color: C.accent6, breakLine: i < list.length - 1 } },
      ]),
      { x, y, w, h, fontSize: size, valign: "top", margin: 0, paraSpaceAfter: 7, isTextBox: true },
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
  s.addText("Wyzwanie Podkarpackiego Centrum Innowacji · HackNation 2026 · zespół CombAIns", {
    x: 0.6, y: 4.75, w: 7, h: 0.35, fontSize: 13, color: C.accent2, bold: true, margin: 0, isTextBox: true,
  });
  s.addNotes(
    "Radar innowacji to jedno miejsce, w którym gmina, szkoła, uczelnia, firma czy inwestor znajdzie polskie innowacje, które już działają. " +
      "Aplikacja sama odkrywa je w otwartych źródłach, ocenia według jawnych kryteriów i pokazuje, gdzie można je zastosować.",
  );

  // ---- 2. Problem ----
  pres.addSection({ title: "Problem i rozwiązanie" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem i rozwiązanie" });
  s.addText("Innowacje już istnieją, ale nikt ich nie widzi", { placeholder: "title" });
  const stats = [
    ["36 500", "projektów Funduszy Europejskich 2021–2027 w jednym arkuszu na dane.gov.pl, bez wyszukiwarki rozwiązań"],
    ["19 000+", "patentów jednostek naukowych w systemie RAD-on, opisanych językiem prawnym"],
    ["~10%", "inwestycji funduszy VC wspieranych ze środków UE ma komponent naukowy (2019–2026)"],
  ];
  stats.forEach(([num, label], i) => {
    const y = 1.25 + i * 1.3;
    s.addText(num, { x: 0.5, y, w: 2.3, h: 0.75, fontSize: 40, bold: true, color: C.accent1, margin: 0, valign: "middle", isTextBox: true });
    s.addText(label, { x: 2.9, y: y + 0.02, w: 2.7, h: 0.75, fontSize: 12, color: C.accent6, margin: 0, valign: "middle", isTextBox: true });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.9, y: 1.25, w: 3.6, h: 3.7, rectRadius: 0.12, fill: { color: C.background2 }, line: { type: "none" }, objectName: "Problem card" });
  s.addText(
    [
      { text: "Informacje są rozproszone", options: { bold: true, breakLine: true } },
      { text: "Projekty UE, patenty, strony urzędów i szkół, wyniki konkursów, zamówienia publiczne.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Katalogi wymagają zgłoszeń", options: { bold: true, breakLine: true } },
      { text: "Każdy obejmuje jeden sektor i szybko się dezaktualizuje.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Skutek", options: { bold: true, breakLine: true } },
      { text: "Gmina nie wie, że inna gmina rozwiązała już ten sam problem.", options: {} },
    ],
    { x: 6.15, y: 1.45, w: 3.15, h: 3.35, fontSize: 14, color: C.text1, valign: "top", margin: 0, isTextBox: true },
  );
  s.addText("Źródła: dane.gov.pl, RAD-on (OPI PIB), xyz.pl na podstawie danych PFR Ventures.", {
    x: 0.5, y: 5.05, w: 9, h: 0.25, fontSize: 9, color: C.accent6, margin: 0, isTextBox: true,
  });
  s.addNotes(
    "Dane o innowacjach istnieją, ale są rozproszone. Lista projektów Funduszy Europejskich to 36,5 tys. wierszy w jednym pliku. RAD-on ma ponad 19 tys. patentów uczelni i instytutów. " +
      "Tylko około 10% inwestycji funduszy VC wspieranych ze środków UE ma komponent naukowy. Katalogi dobrych praktyk wymagają ręcznego zgłaszania.",
  );

  // ---- 3. Solution: process and scale ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem i rozwiązanie" });
  s.addText("Siedem kroków od źródła do decyzji", { placeholder: "title" });
  const steps = [
    ["Odkrywanie", "8 otwartych źródeł danych"],
    ["Rekord", "jeden schemat, bez danych osobowych"],
    ["Klasyfikacja", "obszar i typ innowacji"],
    ["Ocena", "5 jawnych kryteriów"],
    ["Karta", "dane ze źródła i wartości przybliżone"],
    ["Użycie", "wyszukaj, filtruj, porównaj"],
    ["Aktualizacja", "cykliczne sprawdzanie źródeł"],
  ];
  const stepW = 1.25;
  s.addShape(pres.shapes.LINE, { x: 0.5 + 0.2, y: 1.75, w: 6 * (stepW + 0.04), h: 0, line: { color: HEX.accent1, width: 1.5 }, objectName: "Process line" });
  steps.forEach(([head, body], i) => {
    const x = 0.5 + i * (stepW + 0.04);
    s.addShape(pres.shapes.OVAL, { x, y: 1.55, w: 0.4, h: 0.4, fill: { color: C.accent1 }, line: { type: "none" }, objectName: `Step ${i + 1}` });
    s.addText(String(i + 1), { x, y: 1.55, w: 0.4, h: 0.4, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(head, { x, y: 2.1, w: stepW, h: 0.35, fontSize: 14, bold: true, color: C.text1, margin: 0, isTextBox: true });
    s.addText(body, { x, y: 2.45, w: stepW - 0.05, h: 0.75, fontSize: 11, color: C.accent6, valign: "top", margin: 0, isTextBox: true });
  });
  const numbers = [
    ["3 498", "kart innowacji z 16 województw"],
    ["1 625", "kart z Podkarpacia"],
    ["614", "kart z poziomem wdrożenia 4–5: pilotaż lub użycie w praktyce"],
    ["< 0,2 s", "czas wyszukiwania"],
  ];
  numbers.forEach(([num, label], i) => {
    const x = 0.5 + i * 2.3;
    s.addText(num, { x, y: 3.85, w: 2.1, h: 0.7, fontSize: 32, bold: true, color: C.accent1, margin: 0, valign: "middle", isTextBox: true });
    s.addText(label, { x, y: 4.55, w: 2.05, h: 0.75, fontSize: 12, color: C.accent6, margin: 0, valign: "top", isTextBox: true });
  });
  s.addNotes(
    "Radar sam odkrywa innowacje w ośmiu otwartych źródłach, porządkuje je w jeden schemat, klasyfikuje i ocenia. " +
      "Użytkownik niczego nie zgłasza i nie zakłada konta. Baza ma dziś 3 498 kart z 16 województw, w tym 1 625 z Podkarpacia. " +
      "Indeks powstaje z wyprzedzeniem, więc wyszukiwanie trwa ułamek sekundy, a aktualizacja źródeł kilka minut.",
  );

  // ---- 4. Demo: from a need to the card ----
  pres.addSection({ title: "Demo" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Demo" });
  s.addText("Od potrzeby do karty innowacji", { placeholder: "title" });
  screenshot(s, search, 0.5, 1.1, 4.3, "Strona wyszukiwania Radaru innowacji z zapytaniem o e-usługi w urzędzie");
  screenshot(s, card, 5.2, 1.1, 4.3, "Karta innowacji e-urzędu z oceną i źródłami");
  items(s, [
    ["Fraza lub opis potrzeby", "np. „e-usługi w urzędzie”, „robotyka w szkole”"],
    ["Filtry dla 6 grup", "m.in. samorządy (JST), szkoły, uczelnie, firmy"],
    ["Ranking", "70% trafność, 30% ocena potencjału"],
    ["Działa na telefonie", "bez instalacji aplikacji"],
  ], 0.5, 4.2, 4.3, 1.2, 11);
  items(s, [
    ["„Ze źródła”", "wartość z cytatem i linkiem"],
    ["„Przybliżone”", "wartość z reguły; powód pod „dlaczego?”"],
    ["Każde źródło", "z datą sprawdzenia i licencją"],
    ["Brak danych", "opisany wprost, a nie ukryty"],
  ], 5.2, 4.2, 4.3, 1.2, 11);
  s.addNotes(
    "Użytkownik wpisuje frazę lub opis potrzeby. Tu samorząd szuka e-usług w urzędzie i dostaje 156 istniejących rozwiązań. " +
      "Filtry obejmują grupę użytkowników, obszar, województwo i minimalny poziom wdrożenia. JST to jednostki samorządu terytorialnego: gminy, powiaty i województwa. " +
      "Karta pokazuje opis, obszar, instytucję, status wdrożenia, gotowość technologiczną i ocenę. Każda wartość ma etykietę: „ze źródła” z cytatem i linkiem albo „przybliżone” z powodem.",
  );

  // ---- 5. Assessment ----
  pres.addSection({ title: "Ocena i dane" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ocena i dane" });
  s.addText("Jawna ocena według 5 kryteriów", { placeholder: "title" });
  s.addChart(
    pres.charts.BAR,
    [{ name: "Waga", labels: ["Wiarygodność", "Potencjał zastosowania", "Innowacyjność", "Dojrzałość technologiczna (TRL)", "Poziom wdrożenia"], values: [15, 20, 20, 15, 30] }],
    {
      x: 0.4, y: 1.0, w: 6.0, h: 2.1, barDir: "bar",
      chartColors: [HEX.accent5], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11, dataLabelColor: HEX.dk1,
      dataLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
      catAxisLabelFontSize: 11, catAxisLabelColor: HEX.dk1, valAxisHidden: true, valAxisMaxVal: 35,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
      showTitle: true, title: "Wagi kryteriów (suma 100)", titleFontSize: 12, titleColor: HEX.accent6, titleFontFace: "+mn-lt",
    },
  );
  items(s, [
    ["TRL", "poziom gotowości technologii w skali 1–9 Komisji Europejskiej; nie dotyczy innowacji edukacyjnych i administracyjnych"],
    ["Przedział zamiast fałszywej precyzji", "brak danych to nie zero"],
    ["Pewność", "jaka część oceny opiera się na danych ze źródła"],
    ["Potencjał zastosowania z danych", "opis, koszt, liczba sektorów, ogłoszenia o zamówieniach w Biuletynie Zamówień Publicznych (BZP)"],
    ["Powtarzalność", "ten sam rekord daje ten sam wynik; AI nie wystawia oceny"],
  ], 0.5, 3.2, 6.1, 2.1, 12);
  const ah = 3.9;
  s.addImage({ data: assessment.data, x: 7.0, y: 1.0, w: ah * assessment.ratio, h: ah, altText: "Panel oceny na karcie innowacji z kryteriami jako paski", shadow: shadow() });
  s.addText("Skale: TRL (Komisja Europejska), Oslo Manual 2018, Nesta, Interreg Europe.", {
    x: 6.6, y: 5.0, w: 2.9, h: 0.3, fontSize: 9, color: C.accent6, margin: 0, align: "right", isTextBox: true,
  });
  s.addNotes(
    "Pięć kryteriów: poziom wdrożenia, dojrzałość technologiczna, innowacyjność, potencjał zastosowania i wiarygodność. Wagi to jawna propozycja zespołu w wersji v0.1. " +
      "TRL to poziom gotowości technologii od 1 (zasada działania) do 9 (system sprawdzony w użyciu). Brak danych nie oznacza zera, więc pokazujemy przedział. " +
      "Potencjał zastosowania liczymy z danych: opisu, kosztu, liczby sektorów i ogłoszeń o zamówieniach publicznych. Model językowy nie wystawia oceny.",
  );

  // ---- 6. Sources ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Ocena i dane" });
  s.addText("8 otwartych źródeł danych", { placeholder: "title" });
  const head = (text) => ({ text, options: { bold: true, color: C.background1, fill: { color: C.accent1 } } });
  const rows = [
    ["Fundusze Europejskie 2021–2027 (dane.gov.pl)", "projekty z opisem, beneficjentem i miejscem", "967", "CC0 1.0"],
    ["RAD-on (OPI PIB)", "patenty i projekty jednostek naukowych", "927", "CC0 1.0"],
    ["Europejski Urząd Patentowy (EPO)", "patenty europejskie polskich firm i uczelni", "1 164", "CC BY 4.0"],
    ["NCBR: sukcesy beneficjentów", "zakończone projekty z opisem problemu i odbiorców", "300", "opis i link"],
    ["Kohesio (Komisja Europejska)", "zakończone projekty UE 2014–2020", "56", "zasady KE"],
    ["Interreg 2021–2027 (dane.gov.pl)", "projekty transgraniczne", "50", "CC0 1.0"],
    ["Konkurs „Innowacyjny Samorząd”", "nagrodzone wdrożenia samorządów", "42", "cytat i link"],
    ["Biuletyn Zamówień Publicznych (BZP)", "kto kupuje podobne rozwiązania: sygnał popytu", "2 803 ogłoszeń", "informacja publiczna"],
  ];
  s.addTable(
    [[head("Źródło"), head("Co daje"), head("Rekordy"), head("Licencja")], ...rows.map((r) => r.map((t) => ({ text: t })))],
    {
      x: 0.5, y: 1.05, w: 9, colW: [3.0, 3.5, 1.1, 1.4], rowH: 0.36, fontSize: 11, color: HEX.dk1, fontFace: "Calibri",
      border: { type: "solid", pt: 0.5, color: "DDE4EA" }, valign: "middle", margin: 0.05,
    },
  );
  s.addText("Każdy rekord ma źródło, datę danych, datę pobrania i licencję. Awaria jednego źródła nie zatrzymuje pozostałych.", {
    x: 0.5, y: 4.55, w: 9, h: 0.4, fontSize: 13, color: C.text1, margin: 0, valign: "middle", isTextBox: true,
  });
  s.addNotes(
    "Korzystamy tylko z bezpłatnych i legalnych źródeł, bez kluczy API. NCBR to Narodowe Centrum Badań i Rozwoju, BZP to Biuletyn Zamówień Publicznych. " +
      "Rekordy z różnych źródeł o tej samej innowacji łączymy w jedną kartę z osią czasu. Nie pobieramy danych osób: oceniamy innowację, a nie człowieka.",
  );

  // ---- 7. Two use cases: where to apply, who can use it, the next path and its measures ----
  pres.addSection({ title: "Przypadki użycia" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Przypadki użycia" });
  s.addText("Dwa przypadki: gdzie zastosować i co dalej", { placeholder: "title" });
  const useCase = (x, title, lines) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.05, w: 4.4, h: 4.25, rectRadius: 0.1, fill: { color: C.background2 }, line: { type: "none" }, objectName: title });
    s.addText(title, { x: x + 0.2, y: 1.15, w: 4.0, h: 0.45, fontSize: 15, bold: true, color: C.accent1, valign: "middle", margin: 0, isTextBox: true });
    s.addText(
      lines.flatMap(([label, text], i) => [
        { text: `${label}: `, options: { bold: true, color: C.text1 } },
        { text, options: { color: C.text1, breakLine: i < lines.length - 1 } },
      ]),
      { x: x + 0.2, y: 1.65, w: 4.0, h: 3.55, fontSize: 12, valign: "top", margin: 0, paraSpaceAfter: 4, isTextBox: true },
    );
  };
  useCase(0.5, "Samorząd szuka e-usług", [
    ["Zapytanie", "„e-usługi w urzędzie”, grupa: samorządy (JST)"],
    ["Karta", "e-urząd w Gminie Horyniec-Zdrój: wdrożenie pilotażowe, ocena 69 (przedział 53–76)"],
    ["Gdzie zastosować", "administracja publiczna; ICT i cyfryzacja"],
    ["Ścieżka", "replikacja w innej instytucji"],
    ["Mierniki", "liczba instytucji, które przejęły rozwiązanie w ciągu 12 mies.; liczba użytkowników; czas obsługi sprawy"],
    ["Podobne wdrożenia", "Radomyśl Wielki, Sędziszów Małopolski, Cieszanów, Grębów"],
    ["Popyt (BZP)", "Biłgoraj, Wadowice, Dąbrowa Tarnowska"],
  ]);
  useCase(5.1, "Technologia z uczelni", [
    ["Zapytanie", "„elektroda zgrzewanie”"],
    ["Karta", "bezodpadowa technologia elektrod nasadkowych, Politechnika Rzeszowska: prototyp, ocena 43 (przedział 28–63)"],
    ["Dwa źródła w jednej karcie", "grant 2017 → zgłoszenie 2022 → prawo ochronne 2025; wiarygodność 4 z 5"],
    ["Ścieżka", "transfer technologii: licencja lub wspólny projekt badawczo-rozwojowy (B+R)"],
    ["Mierniki", "zapytania od firm; umowa licencyjna lub B+R w ciągu 12 mies.; wzrost TRL o co najmniej 1"],
    ["Kontakt", "strona i e-mail uczelni; centrum transferu technologii"],
  ]);
  s.addNotes(
    "Dwa przypadki z prawdziwych danych. Gmina szuka e-usług: radar pokazuje e-urząd w Horyńcu-Zdroju, gminy z podobnym wdrożeniem i instytucje, które kupują podobne rozwiązania. " +
      "Rekomendowana ścieżka to replikacja w innej instytucji, z miernikami skuteczności. " +
      "Drugi przypadek: technologia Politechniki Rzeszowskiej. Radar łączy projekt badawczy i prawo ochronne w jedną kartę z osią czasu, proponuje transfer technologii i podaje kontakt do uczelni.",
  );

  // ---- 8. Decision tool and deployment ----
  pres.addSection({ title: "Wartość i wdrożenie" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Wartość i wdrożenie" });
  s.addText("Narzędzie do decyzji, gotowe do wdrożenia", { placeholder: "title" });
  s.addText("Dla użytkownika", { x: 0.5, y: 1.05, w: 4.3, h: 0.35, fontSize: 15, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText("Dla PCI i innych organizacji", { x: 5.2, y: 1.05, w: 4.3, h: 0.35, fontSize: 15, bold: true, color: C.accent3, margin: 0, isTextBox: true });
  items(s, [
    ["Porównanie 2–4 kart", "kryteria w wierszach, link do udostępnienia"],
    ["Obserwowane wyszukiwania", "„Nowe od ostatniej wizyty”, bez logowania"],
    ["Oś czasu z kilku źródeł", "grant, patent, nagroda, wdrożenie"],
    ["Kontakt do instytucji", "oficjalna strona i e-mail, bez danych osób"],
    ["Eksport CSV i API JSON", "dane do arkusza, CRM lub innego systemu"],
    ["Wersja na telefon", "bez instalacji aplikacji"],
  ], 0.5, 1.55, 4.4, 3.7, 13);
  items(s, [
    ["Region w konfiguracji", "inne centrum uruchamia radar bez zmian w kodzie"],
    ["Jedno źródło = jeden moduł", "nowe źródło to jedna funkcja"],
    ["Lekka infrastruktura", "SQLite, zwykły serwer, bez GPU i opłat"],
    ["Bezpieczeństwo", "bez logowania i bez danych osobowych; ocena innowacji, a nie osób (AI Act)"],
    ["Anonimowa analityka", "popularne obszary i karty, bez danych o osobach"],
    ["Licencja EUPL-1.2", "tylko komponenty z otwartymi licencjami"],
  ], 5.2, 1.55, 4.3, 3.7, 13);
  s.addNotes(
    "Radar nie kończy się na liście: można porównać karty, obserwować wyszukiwania, skontaktować się z instytucją, wyeksportować dane do CSV i pobrać je przez API. " +
      "Region i źródła są w konfiguracji, a nie w kodzie, więc radar może działać w każdym województwie. Nie ma logowania ani danych osobowych. " +
      "Fundusze VC budują własne platformy danych do szukania projektów, np. EQT Motherbrain. PFR Ventures w programie Starter Science ocenia, czy fundusze umieją znaleźć projekty z nauki. Radar daje tę metodę PCI, samorządom i uczelniom.",
  );

  // ---- 9. Next steps ----
  s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Wartość i wdrożenie" });
  radar(s, 8.4, 4.4, 1.5, 55);
  s.addText("Co dalej", { x: 0.6, y: 0.45, w: 6, h: 0.7, fontSize: 32, bold: true, color: C.background1, margin: 0, isTextBox: true });
  const next = [
    ["Kalibracja wag", ""],
    ["Wyszukiwanie semantyczne", "dopasowanie po znaczeniu, nie tylko po słowach"],
    ["Strony szkół i samorządów", "automatyczne czytanie aktualności i projektów"],
    ["Panel analityka PCI", "potwierdzanie wartości z zapisem powodu"],
    ["Kolejne źródła", "CORDIS, OpenAlex, wyniki Erasmus+"],
  ];
  next.forEach(([title, body], i) => {
    const y = 1.45 + i * 0.68;
    s.addText(String(i + 1), { x: 0.6, y, w: 0.4, h: 0.5, fontSize: 20, bold: true, color: C.accent2, valign: "middle", margin: 0, isTextBox: true });
    s.addText(
      [
        { text: `${title}  `, options: { bold: true, color: C.background1 } },
        { text: body, options: { color: "E6F3FB" } },
      ],
      { x: 1.1, y, w: 6.0, h: 0.5, fontSize: 16, valign: "middle", margin: 0, isTextBox: true },
    );
  });
  s.addNotes(
    "Po hackathonie chcemy skalibrować wagi, dodać wyszukiwanie semantyczne, czytać strony szkół i samorządów, zbudować panel analityka i dodać kolejne źródła.",
  );

  // ---- 10. Team ----
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Wartość i wdrożenie" });
  s.addText(
    [
      { text: "Zespół ", options: { color: C.text1 } },
      { text: "CombAIns", options: { color: C.accent1 } },
    ],
    { placeholder: "title" },
  );
  const team = [
    ["team-filip.jpg", "Filip", "Langiewicz", "filiplangiewicz"],
    ["team-mikolaj.jpg", "Mikołaj", "Rowicki", "mikolajrowicki"],
    ["team-maciej.jpg", "Maciej", "Momot", "maciej-momot"],
  ];
  team.forEach(([file, first, last, handle], i) => {
    const cx = 1.95 + i * 3.05;
    const size = 1.9;
    s.addImage({ path: path.join(IMG, file), x: cx - size / 2, y: 1.15, w: size, h: size, rounding: true, altText: `${first} ${last}` });
    s.addText(
      [
        { text: first, options: { breakLine: true } },
        { text: last, options: {} },
      ],
      { x: cx - 1.4, y: 3.2, w: 2.8, h: 0.95, fontSize: 22, bold: true, color: C.text1, align: "center", valign: "top", margin: 0, isTextBox: true },
    );
    s.addText([{ text: `in/${handle}`, options: { hyperlink: { url: `https://www.linkedin.com/in/${handle}` } } }], {
      x: cx - 1.4, y: 4.2, w: 2.8, h: 0.35, fontSize: 13, color: C.accent1, align: "center", margin: 0, isTextBox: true,
    });
  });
  s.addNotes("Zespół CombAIns: Filip Langiewicz, Mikołaj Rowicki i Maciej Momot. Dziękujemy.");

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
