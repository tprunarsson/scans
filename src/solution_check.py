"""Athugar leysta lausn eftir á og býr til mannlæsilegar aðvaranir fyrir
hverja mjúka skorðu sem var ekki að fullu uppfyllt (nemandi fékk ekki að
klára snemma, lenti á ranga/rétta stað eða deild sem hann bað ekki um, fékk
ekki umbeðið frí, eða - alvarlegast - lenti í tilbúna "Vantar pláss" plássinu
sem þýðir að raunveruleg pláss dugðu ekki til). Þetta er sami útreikningur og
markfallið í model_generator*.py refsar fyrir, bara í læsilegu formi fyrir
notandann í staðinn fyrir tölu í hlutlægnisfallinu."""
from vikur import Vikur

def check_solution(x, M):
  V = Vikur()
  sym_vikur = V.sym

  warnings = []

  # Klára klíník snemma
  t = sum(x[s,c,v,d].X for s in M.klara_snemma
          for c in M.klinik
          for v in set(M.klinik[c]).difference(M.auka_vikur)
          if sym_vikur[v] >= sym_vikur[M.klara_snemma[s]] for d in M.klinik[c][v])
  t = int(t + 0.5)
  if t > 0:
    w = f'{t} nemendur fengu ekki að klára alla klíník á tilgreindum tíma:'
    for s in M.klara_snemma:
      for c in M.klinik:
        for v in set(M.klinik[c]).difference(M.auka_vikur):
          if sym_vikur[v] >= sym_vikur[M.klara_snemma[s]]:
            for d in M.klinik[c][v]:
              if x[s,c,v,d].X > 0:
                w += f'{s} ({M.nemendur[s].nafn}):\n'
                w += f'\t átti að klára fyrir viku {M.klara_snemma[s]}\n'
                w += f'\t en var sett/ur í námskeið {c} í viku {v}\n'
    warnings.append(w)

  # Klára klíník snemma (sérstök námskeið)
  t = sum(x[s,c,v,d].X for s in M.klara_snemma_serstakt
          for c in M.klara_snemma_serstakt[s]
          for v in set(M.klinik[c]).difference(M.auka_vikur)
          if sym_vikur[v] >= sym_vikur[M.klara_snemma_serstakt[s][c]] for d in M.klinik[c][v])
  t = int(t + 0.5)
  if t > 0:
    w = f'{t} nemendur fengu ekki að klára klíník í sérstöku námskeiði á tilgreindum tíma:'
    for s in M.klara_snemma_serstakt:
      for c in M.klara_snemma_serstakt[s]:
        for v in set(M.klinik[c]).difference(M.auka_vikur):
          if sym_vikur[v] >= sym_vikur[M.klara_snemma_serstakt[s][c]]:
            for d in M.klinik[c][v]:
              if x[s,c,v,d].X > 0:
                w += f'{s} ({M.nemendur[s].nafn}):\n'
                w += f'\t átti að klára námsekið {c} fyrir viku {M.klara_snemma_serstakt[s][c]}\n'
                w += f'\t en var sett/ur í klíník í viku {v}\n'
    warnings.append(w)

  # Ekki ákveðnir staðir, "false negative"
  t = sum(x[s,c,v,d].X for s in M.nemendur
          for c in M.klinik
          for v in M.klinik[c]
          for d in { d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.ekki_sami_stadur[s][c] })
  t = int(t + 0.5)
  if t > 0:
    w = f'{t} nemendur voru settir á stað sem þeir ættu ekki að vera á:\n'
    for s in M.nemendur:
      for c in M.klinik:
        for v in M.klinik[c]:
          for d in { d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.ekki_sami_stadur[s][c] }:
            if x[s,c,v,d].X > 0:
              w += f'{s} ({M.nemendur[s].nafn}):\n'
              w += f'\t átti ekki að vera á staðnum {M.ekki_sami_stadur[s][c]} í námskeiði {c}\n'
              w += f'\t en var sett/ur á staðinn {M.klinik[c][v][d].stadur}\n'
    warnings.append(w)

  # Ákveðnir staðir, "false positive"
  t = sum(x[s,c,v,d].X for s in M.nemendur
          for c in M.klinik
          for v in M.klinik[c]
          for d in { d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.stadir[c].difference(M.sami_stadur[s][c]) })
  t = int(t + 0.5)
  if t > 0:
    w = f'{t} nemendur voru settir á stað sem var ekki sérstaklega beðið um:'
    for s in M.nemendur:
      for c in M.klinik:
        for v in M.klinik[c]:
          for d in { d for d in M.klinik[c][v] if M.klinik[c][v][d].stadur in M.stadir[c].difference(M.sami_stadur[s][c]) }:
            if x[s,c,v,d].X > 0:
              w += f'{s}:\t{M.klinik[c][v][d].stadur}\n'
    warnings.append(w)

  # Auka pláss
  t = sum(x[s,c,v,'Vantar pláss'].X for s in M.nemendur
          for c in M.klinik
          for v in M.auka_vikur & set(M.klinik[c]))
  t = int(t + 0.5)
  if t > 0:
    w = f'-----Alvarleg villa-----: {t} nemendur fengu ekki pláss. Útskýringar á þessu geta verið:\n'
    w += f'\t- Það vantar pláss í einu eða fleiri námskeiðum\n'
    w += f'\t- Eitt eða fleiri valnámskeið skarast á þann hátt að enginn / of fáir geta tekið ákveðna klíník í sumum vikum\n'
    w += f'\t- Nemandi er með nauðsynlegt frí (undir fri_skilyrt) sem er ekki hægt að uppfylla m.t.t. skráninga\n'

    w += f'Nemendur og námskeið sem var ekki hægt að uppfylla:\n'
    for s in M.nemendur:
      for c in M.klinik:
        for v in M.auka_vikur & set(M.klinik[c]):
          if x[s,c,v,'Vantar pláss'].X > 0:
            w += f'{s}:\t{c}\n'
    warnings.append(w)

  # Ákveðnar deildir, "false negative"
  t = sum(x[s,c,v,d].X for s in M.sama_deild
          for c in M.sama_deild[s]
          for d in set(M.klinik[c]).difference(M.sama_deild[s][c])
          for v in M.vikur if d in M.klinik[c][v])
  t = int(t + 0.5)
  if t > 0:
    w = f'{t} nemendur fengu ekki að fara á umbeðnar deildir.\n'
    w += f'Kannski vantar pláss í þær deildir?\n'
    for s in M.sama_deild:
      for c in M.sama_deild[s]:
        for d in M.sama_deild[s][c]:
          for v in M.vikur:
            if d in M.klinik[c][v]:
              if x[s,c,v,d].X > 0:
                w += f'{s} ({M.nemendur[s].nafn}):\n'
                w += f'\t átti að vera á ' + ' eða '.join(deild for deild in M.sama_deild[s][c]) + f' í námskeiði {c}\n'
                w += f'\t en var sett/ur á deildina {d}\n'
    warnings.append(w)

  # Ekki ákveðnar deildir, "false negative"
  t = sum(x[s,c,v,d].X for s in M.ekki_sama_deild
          for c in M.ekki_sama_deild[s]
          for d in M.ekki_sama_deild[s][c]
          for v in M.vikur if d in M.klinik[c][v])
  t = int(t + 0.5)
  if t > 0:
    w = f'{t} nemendur voru settir á deild sem þeir ættu ekki að vera á.\n'
    w += f'Kannski vantar pláss í aðrar deildir?\n'
    for s in M.ekki_sama_deild:
      for c in M.ekki_sama_deild[s]:
        for d in M.ekki_sama_deild[s][c]:
          for v in M.vikur:
            if d in M.klinik[c][v]:
              if x[s,c,v,d].X > 0:
                w += f'{s} ({M.nemendur[s].nafn}):\n'
                w += f'\t átti ekki að vera á deildinni {d} í námskeiði {c}\n'
                w += f'\t en var sett/ur á hana\n'
    warnings.append(w)

  # Frí
  t = sum(x[s,c,v,d].X for s in M.fri_osk
          for c in M.klinik
          for v in M.klinik[c] if v > 0
          for d in M.klinik[c][v]
          if len(set(M.fri_osk[s]) & set(M.klinik_vikur[c][v])) > 0)
  t = int(t + 0.5)
  if t > 0:
    w = f'{t} tilfelli urðu þar sem nemandi fékk ekki ósk um frí uppfyllta.\n'
    for s in M.fri_osk:
      for c in M.klinik:
        for v in M.klinik[c]:
          if v > 0:
            for d in M.klinik[c][v]:
              if len(set(M.fri_osk[s]) & set(M.klinik_vikur[c][v])) > 0:
                if x[s,c,v,d].X > 0:
                  w += f'{s} ({M.nemendur[s].nafn}):\n'
                  plural = ''
                  if len(M.fri_osk[s]) > 1:
                    plural = 'm'
                  w += f'\t óskaði um frí í viku{plural} ' + ' og '.join(f'{v:02d}' for v in M.fri_osk[s]) + f' en var sett/ur í klíník í námskeiði {c} í viku {v}\n'
    warnings.append(w)

  return warnings