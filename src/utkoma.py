"""
Býr til JSON-úttak (output.json) úr leystu líkani: eina töflu per námskeið
með deildarlista og lausum plássum ("mrs_radad_<námskeið>"), eina sameinaða
stundatöflu ("stundatafla"), og eitt yfirlit yfir skráningar á móti plássum
("skraningar"). gas/Export.gs les þetta aftur inn og býr til eitt Google
Sheet blað per lykil í úttakinu.

Dagsetningar koma beint úr `date_lookup` (byggt úr Lotur blaðinu í
input.json af main.py) í stað þess að vera reiknaðar út frá viku+ártali -
þannig endurtekur þetta ekki vikutalningarvilluna sem fannst og var lagfærð
fyrr í þessu verkefni (sjá README.md).
"""

def generate_output(M, x, date_lookup):
  """M: ModelData (sjá model_data.py). x: leystu breyturnar úr
  model_generator*.py, x[s,c,v,d].X > 0 þýðir að nemandi s sé settur á deild
  d í viku v fyrir námskeið c. date_lookup: dict {(námskeið, vika): dagsetning}."""
  result = {}

  # ---- mrs_radad_<námskeið>: deildarlisti per námskeið, með lausum plássum ----
  for c in M.klinik:
    rows = []
    for v in sorted(v for v in M.klinik[c] if v > 0):  # v <= 0 er tilbúna "Vantar pláss" yfirfljótsvikan, ekki hluti af úttaki
      if len(M.klinik[c][v]) == 0:
        continue
      dags = date_lookup.get((c, v), '')
      for d in M.klinik[c][v]:
        deild = M.klinik[c][v][d]
        skradir = [s for s in M.nemendur if x[s, c, v, d].X > 0]
        for s in skradir:
          rows.append({
            'vika': v, 'dagsetning': dags, 'deild': d,
            'notandanafn': s, 'nafn': M.nemendur[s].nafn.title(),
            'kennitala': M.nemendur[s].kennitala, 'farsimi': M.nemendur[s].farsimi,
            'vidfang': deild.vidfang, 'plass': deild.plass,
            'deildarstjori': deild.stjori.title(), 'netfang_deildar': deild.netfang,
            'simanumer': deild.simanumer,
          })
        # Laus pláss fá sína eigin línu (auðar nemendasúlur) svo heildarfjöldi
        # lína á deild jafngildi alltaf plássafjöldanum - gagnlegt yfirlit
        # yfir hvað er enn laust, ekki bara hvað er fullt.
        for _ in range(deild.plass - len(skradir)):
          rows.append({
            'vika': v, 'dagsetning': dags, 'deild': d,
            'notandanafn': '', 'nafn': '', 'kennitala': '', 'farsimi': '',
            'vidfang': deild.vidfang, 'plass': deild.plass,
            'deildarstjori': deild.stjori.title(), 'netfang_deildar': deild.netfang,
            'simanumer': deild.simanumer,
          })
    result[f'mrs_radad_{c}'] = rows

  # ---- stundatafla: löng skráning, ein lína per (nemandi, vika sem hann er í) ----
  stundatafla_rows = []
  for s in M.nemendur:
    for c in M.val_nemenda[s]:
      if M.val_nemenda[s][c] > 0:
        for v in M.val_vikur[c]:
          stundatafla_rows.append({
            'notandanafn': s, 'namskeid': c, 'vika': v, 'dagsetning': date_lookup.get((c, v), ''),
          })
    for c in M.klinik:
      for v in M.klinik[c]:
        if v <= 0:
          continue
        for d in M.klinik[c][v]:
          if x[s, c, v, d].X > 0:
            stundatafla_rows.append({
              'notandanafn': s, 'namskeid': c, 'vika': v, 'dagsetning': date_lookup.get((c, v), ''),
            })
  result['stundatafla'] = stundatafla_rows

  # ---- skraningar: fjöldi skráðra á móti plássum, per (námskeið, vika) ----
  skraningar_rows = []
  for c in M.klinik:
    for v in M.klinik[c]:
      if v <= 0 or len(M.klinik[c][v]) == 0:
        continue
      skradir = sum(1 for s in M.nemendur for d in M.klinik[c][v] if x[s, c, v, d].X > 0)
      plass_alls = sum(M.klinik[c][v][d].plass for d in M.klinik[c][v])
      skraningar_rows.append({
        'namskeid': c, 'vika': v, 'dagsetning': date_lookup.get((c, v), ''),
        'skradir': skradir, 'plass_alls': plass_alls,
      })
  result['skraningar'] = skraningar_rows

  return result
