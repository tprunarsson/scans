/**
 * Flytja gögn út sem input.json (fyrir main.py) og flytja niðurstöður inn úr
 * output.json (frá main.py) sem ný blöð í þessu vinnuskjali.
 *
 * Vinnuflæði (beint á milli vafra og tölvu - engin Google Drive milliliður):
 *  1. "Sækja gögn" (SaekjaGognDialog.html) - opnar glugga með hnappi sem
 *     sækir input.json beint í niðurhals (Downloads) möppuna þína, eins og
 *     hvaða skráarniðurhal sem er.
 *  2. Keyrðu á þinni vél: python3 main.py input.json output.json
 *  3. "Hlaða upp niðurstöðum" (HladaUppDialog.html) - opnar glugga þar sem
 *     þú velur output.json af tölvunni þinni (venjulegur skráarveljari).
 *     Býr til/yfirskrifar eitt blað fyrir hvern lykil í JSON-inu (t.d.
 *     "stundatafla", "skraningar", "mrs_radad_<námskeið>" o.s.frv.), auk
 *     "Keyrsluskilaboð" fyrir viðvaranir.
 */

const SHEET_KEYRSLUSKILABOD = 'Keyrsluskilaboð';

const INPUT_DATA_SHEETS = [
  'Nemendur', 'Skraningar', 'Lotur', 'Deildir',
  'fri_skilyrt', 'klara_snemma', 'klara_snemma_serstakt', 'akvedin_rodun',
  'sami_stadur', 'ekki_sami_stadur', 'sama_deild', 'ekki_sama_deild', 'fri_osk',
];

function exportInputJson() {
  const json = buildInputJsonString();

  const template = HtmlService.createTemplateFromFile('SaekjaGognDialog');
  template.dataJson = JSON.stringify(json);

  const html = template.evaluate().setWidth(380).setHeight(140);
  SpreadsheetApp.getUi().showModalDialog(html, 'Sækja gögn');
}

function buildInputJsonString() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const data = {};
  INPUT_DATA_SHEETS.forEach(sheetName => {
    const sheet = ss.getSheetByName(sheetName);
    if (!sheet) return;
    data[sheetName] = sheetToRecords(sheet);
  });
  return JSON.stringify(data, null, 2);
}

function importOutputJson() {
  const html = HtmlService.createHtmlOutputFromFile('HladaUppDialog')
    .setWidth(400).setHeight(150);
  SpreadsheetApp.getUi().showModalDialog(html, 'Hlaða upp niðurstöðum');
}

function processOutputJson(jsonText) {
  const data = JSON.parse(jsonText);
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const messages = data['messages'] || [];
  writeMessagesSheet(ss, data['status'], messages);

  Object.keys(data).forEach(key => {
    if (key === 'status' || key === 'messages') return;
    const records = data[key];
    if (!Array.isArray(records)) return;
    // "Út - " forskeytið tryggir að úttaksblöð rekist aldrei á inntaksblöð með
    // sama (eða aðeins hástöfum ólíku - blaðanöfn eru ekki há-/lágstafanæm í
    // Sheets) nafni, t.d. úttakslykillinn "skraningar" á móti inntaksblaðinu
    // "Skraningar" - sem áður olli því að staðfestingarreglur af innsláttarblaðinu
    // læktust óvart við úttaksgögnin.
    writeRecordsSheet(ss, 'Út - ' + key, records);
  });

  return `Lokið. Staða: ${data['status']}. ${messages.length} skilaboð - sjá "${SHEET_KEYRSLUSKILABOD}".`;
}

function sheetToRecords(sheet) {
  const values = sheet.getDataRange().getValues();
  if (values.length < 1) return [];
  const headers = values[0];
  return values.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => {
      let v = row[i];
      if (v instanceof Date) {
        v = Utilities.formatDate(v, Session.getScriptTimeZone(), 'yyyy-MM-dd');
      } else if (v === '') {
        v = null;
      }
      obj[h] = v;
    });
    return obj;
  });
}

function writeRecordsSheet(ss, sheetName, records) {
  let sheet = ss.getSheetByName(sheetName);
  if (!sheet) sheet = ss.insertSheet(sheetName);
  sheet.clear();
  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).clearDataValidations();

  if (records.length === 0) return;

  const headers = Object.keys(records[0]);
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  const rows = records.map(r => headers.map(h => (r[h] === null || r[h] === undefined) ? '' : r[h]));
  sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
}

function writeMessagesSheet(ss, status, messages) {
  let sheet = ss.getSheetByName(SHEET_KEYRSLUSKILABOD);
  if (!sheet) sheet = ss.insertSheet(SHEET_KEYRSLUSKILABOD);
  sheet.clear();
  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).clearDataValidations();
  sheet.getRange(1, 1).setValue(`Staða: ${status} (${new Date().toLocaleString()})`);
  sheet.getRange(2, 1, 1, 2).setValues([['Alvarleiki', 'Skilaboð']]);
  if (messages.length > 0) {
    sheet.getRange(3, 1, messages.length, 2).setValues(messages.map(m => [m.level, m.text]));
  }
}
