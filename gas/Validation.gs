/**
 * Staðfesting og lagfæring gagna fyrir stundatöflu-vinnuskjalið.
 *
 * "Stundatafla" valmyndin bætir við tveimur aðgerðum:
 *
 *  - "Staðfesta gögn": athugar tilvísanir (netfang/námskeið/deild/staður) og
 *    vika/dagsetning misræmi. Niðurstöður fara í "Villur" blaðið. Villur eru
 *    flokkaðar í þrjá flokka eftir því hversu örugg lagfæringin er:
 *
 *      1. Tilvísun sem finnst ekki (t.d. netfang ekki í nemendaskrá) -
 *         AÐEINS ábending. Ekki hægt að álykta örugga lagfæringu (gæti verið
 *         innsláttarvilla EÐA gild brottfallin skráning), svo þetta þarf
 *         alltaf handvirka skoðun.
 *
 *      2. Lítið misræmi milli viku og dagsetningar (±2 vikur eða minna) -
 *         LAGAÐ SJÁLFKRAFA. Þetta er undirskrift þekkta villan þar sem
 *         vikutalning miðast við "fyrsta mánudag" í stað "fyrsta fimmtudags"
 *         - dagsetningin er áreiðanlegri (mannlega valin) en vikunúmerið sem
 *         er reiknað eftir rangri reglu, svo vika er leiðrétt út frá
 *         dagsetningu.
 *
 *      3. Stórt misræmi milli viku og dagsetningar (>2 vikur) - TILLAGA sem
 *         þarfnast samþykkis. Svona stökk er líklegar merki um að
 *         dagsetningin sjálf sé röng (t.d. dagur/mánuður víxlað við
 *         innslátt) heldur en að vikutalningin sé kerfisbundið skökk, svo
 *         hér er ekki nógu öruggt að breyta neinu án staðfestingar. Ef
 *         víxlun á degi/mánuði leysir misræmið er það sett fram sem tillaga.
 *
 *  - "Beita samþykktum lagfæringum": les "Villur" blaðið, og fyrir hverja
 *    línu sem er merkt "Tillaga - þarfnast samþykkis" OG hefur verið hökuð
 *    við í "Samþykkja" dálkinum, skrifar tillöguna inn í upprunablaðið.
 */

const SHEET_NEMENDUR = 'Nemendur';
const SHEET_VIDMID = 'Vidmid';
const SHEET_VILLUR = 'Villur';

// Mismunur á viku, í vikum, sem er talinn nógu lítill til að treysta
// dagsetningunni og laga vikuna sjálfkrafa. Allt umfram þetta fer í
// "tillaga - þarfnast samþykkis" í staðinn. Stillanlegt eftir þörfum.
const DRIFT_THRESHOLD = 2;

const STADA_ABENDING = 'Aðeins ábending - þarfnast handvirkrar skoðunar';
const STADA_LAGAD_SJALFKRAFA = 'Lagað sjálfkrafa (treyst á dagsetningu)';
const STADA_TILLAGA = 'Tillaga - þarfnast samþykkis';
const STADA_BEITT = 'Beitt af notanda';

const REFERENCE_CHECKS = {
  'Skraningar': { notandanafn: true, namskeid: true },
  'Lotur': { namskeid: true },
  'Deildir': { namskeid: true },
  'fri_skilyrt': { notandanafn: true },
  'klara_snemma': { notandanafn: true },
  'klara_snemma_serstakt': { notandanafn: true, namskeid: true },
  'akvedin_rodun': { notandanafn: true, namskeid: true, deild: true },
  'sami_stadur': { notandanafn: true, namskeid: true, stadur: true },
  'ekki_sami_stadur': { notandanafn: true, namskeid: true, stadur: true },
  'sama_deild': { notandanafn: true, namskeid: true, deild: true },
  'ekki_sama_deild': { notandanafn: true, namskeid: true, deild: true },
  'fri_osk': { notandanafn: true },
};

const WEEK_DATE_CHECKS = ['Lotur', 'Deildir'];

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Stundatafla')
    .addItem('Staðfesta gögn', 'validateAll')
    .addItem('Beita samþykktum lagfæringum', 'applyApprovedFixes')
    .addSeparator()
    .addItem('Sækja gögn', 'exportInputJson')
    .addItem('Hlaða upp niðurstöðum', 'importOutputJson')
    .addToUi();
}

function validateAll() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const problems = [];

  // ---- 1. Tilvísanaeftirlit: aðeins ábending, engin sjálfvirk lagfæring ----
  const validNemendur = new Set(readColumn(ss, SHEET_NEMENDUR, 'notandanafn'));
  const validNamskeid = new Set(readColumn(ss, SHEET_VIDMID, 'namskeid'));
  const validDeild = new Set(readColumn(ss, SHEET_VIDMID, 'deild'));
  const validStadur = new Set(readColumn(ss, SHEET_VIDMID, 'stadur'));
  const lookups = { notandanafn: validNemendur, namskeid: validNamskeid, deild: validDeild, stadur: validStadur };

  for (const sheetName in REFERENCE_CHECKS) {
    const sheet = ss.getSheetByName(sheetName);
    if (!sheet) continue;
    const cols = REFERENCE_CHECKS[sheetName];
    const data = getSheetAsObjects(sheet);
    data.rows.forEach((row, i) => {
      for (const colName in cols) {
        const val = row[colName];
        if (val === undefined || val === '' || val === null) continue;
        if (!lookups[colName].has(String(val))) {
          problems.push({
            tegund: 'Tilvísun', stada: STADA_ABENDING,
            lysing: `${sheetName}!röð ${i + 2}: "${colName}" gildið "${val}" fannst ekki í tilvísanalista.`,
            blad: sheetName, rod: i + 2, dalkur: colName, gildi: val, tillaga: '',
          });
        }
      }
    });
  }

  // ---- 2 & 3. Vika/dagsetning: sjálfvirk lagfæring eða tillaga ----
  WEEK_DATE_CHECKS.forEach(sheetName => {
    const sheet = ss.getSheetByName(sheetName);
    if (!sheet) return;
    const data = getSheetAsObjects(sheet);
    const vikaCol = data.headers.indexOf('vika') + 1;

    data.rows.forEach((row, i) => {
      const vika = row['vika'];
      const dags = row['dagsetning'];
      if (!vika || !(dags instanceof Date)) return;

      const isoVika = isoWeekNumber(dags);
      if (Number(vika) === isoVika) return;

      const rowNum = i + 2;
      const diff = circularWeekDiff(Number(vika), isoVika);

      if (diff <= DRIFT_THRESHOLD) {
        // Lítið, kerfisbundið misræmi - treyst á dagsetningu, vika löguð sjálfkrafa.
        sheet.getRange(rowNum, vikaCol).setValue(isoVika);
        problems.push({
          tegund: 'Vika/dagsetning', stada: STADA_LAGAD_SJALFKRAFA,
          lysing: `${sheetName}!röð ${rowNum}: vika ${vika} breytt í ${isoVika} (skv. dagsetningu ${formatDate(dags)}).`,
          blad: sheetName, rod: rowNum, dalkur: 'vika', gildi: vika, tillaga: isoVika,
        });
      } else {
        // Stórt misræmi - ekki nógu öruggt til að laga sjálfkrafa.
        const swapped = trySwapDayMonth(dags);
        if (swapped && isoWeekNumber(swapped) === Number(vika)) {
          problems.push({
            tegund: 'Vika/dagsetning', stada: STADA_TILLAGA,
            lysing: `${sheetName}!röð ${rowNum}: dagsetning ${formatDate(dags)} passar ekki við viku ${vika}, ` +
                    `en ef dagur/mánuður er víxlað fæst ${formatDate(swapped)} sem passar við viku ${vika}.`,
            blad: sheetName, rod: rowNum, dalkur: 'dagsetning', gildi: formatDate(dags), tillaga: formatDate(swapped),
          });
        } else {
          problems.push({
            tegund: 'Vika/dagsetning', stada: STADA_TILLAGA,
            lysing: `${sheetName}!röð ${rowNum}: vika ${vika} skráð fyrir ${formatDate(dags)}, en samkvæmt ` +
                    `ISO-vikutali er sú dagsetning í viku ${isoVika}. Stórt misræmi - engin örugg tillaga fannst.`,
            blad: sheetName, rod: rowNum, dalkur: 'vika', gildi: vika, tillaga: isoVika,
          });
        }
      }
    });
  });

  writeProblems(ss, problems);

  const autoFixed = problems.filter(p => p.stada === STADA_LAGAD_SJALFKRAFA).length;
  const needsApproval = problems.filter(p => p.stada === STADA_TILLAGA).length;
  const infoOnly = problems.filter(p => p.stada === STADA_ABENDING).length;
  SpreadsheetApp.getUi().alert(
    'Staðfesting lokið.\n' +
    `${autoFixed} atriði löguð sjálfkrafa.\n` +
    `${needsApproval} tillögur þarfnast samþykkis (hakið við í "Samþykkja" dálki í "${SHEET_VILLUR}", keyrið svo "Beita samþykktum lagfæringum").\n` +
    `${infoOnly} ábendingar um tilvísanir sem þarf að skoða handvirkt (engin sjálfvirk lagfæring möguleg).`
  );
}

function applyApprovedFixes() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const villurSheet = ss.getSheetByName(SHEET_VILLUR);
  if (!villurSheet) {
    SpreadsheetApp.getUi().alert('Ekkert "Villur" blað fannst - keyrið "Staðfesta gögn" fyrst.');
    return;
  }

  const data = readVillurRows(villurSheet);
  const stadaCol = data.headers.indexOf('Staða') + 1;
  let applied = 0;

  data.rows.forEach(row => {
    if (row['Staða'] !== STADA_TILLAGA) return;
    if (row['Samþykkja'] !== true) return;

    const targetSheet = ss.getSheetByName(row['Blað']);
    if (!targetSheet) return;
    const targetData = getSheetAsObjects(targetSheet);
    const colIndex = targetData.headers.indexOf(row['Dálkur']) + 1;
    if (colIndex <= 0) return;

    let newValue = row['Tillaga'];
    if (row['Dálkur'] === 'dagsetning') {
      newValue = parseDDMMYYYY(String(newValue));
    }
    targetSheet.getRange(row['Röð'], colIndex).setValue(newValue);
    villurSheet.getRange(row._sheetRow, stadaCol).setValue(STADA_BEITT);
    applied++;
  });

  SpreadsheetApp.getUi().alert(`${applied} samþykktar lagfæringar voru framkvæmdar.`);
}

/** ISO 8601 vikunúmer: vika 1 er vikan sem inniheldur fyrsta fimmtudag ársins. */
function isoWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = (d.getUTCDay() + 6) % 7; // mánudagur = 0
  d.setUTCDate(d.getUTCDate() - dayNum + 3); // næsti fimmtudagur
  const firstThursday = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  const diffDays = (d - firstThursday) / 86400000;
  return 1 + Math.round(diffDays / 7);
}

/** Fjarlægð milli tveggja vikunúmera, með hringrás yfir áramót (vika 52 <-> vika 1). */
function circularWeekDiff(a, b) {
  const raw = Math.abs(a - b);
  return Math.min(raw, 52 - raw);
}

/** Skilar dagsetningu með degi og mánuði víxluðum, eða null ef víxlun er ekki gild/þýðingarlaus. */
function trySwapDayMonth(date) {
  const day = date.getDate();
  const month = date.getMonth() + 1;
  if (day > 12 || month > 12 || day === month) return null;
  return new Date(date.getFullYear(), day - 1, month);
}

function formatDate(date) {
  return Utilities.formatDate(date, Session.getScriptTimeZone(), 'dd/MM/yyyy');
}

function parseDDMMYYYY(str) {
  const parts = str.split('/');
  return new Date(Number(parts[2]), Number(parts[1]) - 1, Number(parts[0]));
}

function readColumn(ss, sheetName, colName) {
  const sheet = ss.getSheetByName(sheetName);
  if (!sheet) return [];
  return getSheetAsObjects(sheet).rows
    .map(r => r[colName])
    .filter(v => v !== undefined && v !== '' && v !== null)
    .map(String);
}

function getSheetAsObjects(sheet) {
  const values = sheet.getDataRange().getValues();
  const headers = values[0];
  const rows = values.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => { obj[h] = row[i]; });
    return obj;
  });
  return { headers, rows };
}

/** Sértækur lesari fyrir "Villur" blaðið: fyrirsagnir eru í röð 2 (röð 1 er tímastimpill). */
function readVillurRows(sheet) {
  const values = sheet.getDataRange().getValues();
  if (values.length < 2) return { headers: [], rows: [] };
  const headers = values[1];
  const rows = values.slice(2).map((row, i) => {
    const obj = { _sheetRow: i + 3 };
    headers.forEach((h, j) => { obj[h] = row[j]; });
    return obj;
  });
  return { headers, rows };
}

function writeProblems(ss, problems) {
  let sheet = ss.getSheetByName(SHEET_VILLUR);
  if (!sheet) sheet = ss.insertSheet(SHEET_VILLUR);
  sheet.clear();
  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).clearDataValidations();

  const headers = ['Tegund', 'Staða', 'Lýsing', 'Blað', 'Röð', 'Dálkur', 'Núverandi gildi', 'Tillaga', 'Samþykkja'];
  sheet.getRange(1, 1).setValue(`Staðfesting keyrð: ${new Date().toLocaleString()}`);
  sheet.getRange(2, 1, 1, headers.length).setValues([headers]);

  if (problems.length === 0) return;

  const rows = problems.map(p => [p.tegund, p.stada, p.lysing, p.blad, p.rod, p.dalkur, p.gildi, p.tillaga, false]);
  sheet.getRange(3, 1, rows.length, headers.length).setValues(rows);

  problems.forEach((p, i) => {
    if (p.stada === STADA_TILLAGA) {
      sheet.getRange(3 + i, 9).insertCheckboxes();
    }
  });
}
