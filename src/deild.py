from dataclasses import dataclass

@dataclass
class Deild:
  """Eitt klínískt pláss: tiltekin deild, í tiltekinni viku, fyrir tiltekið námskeið.

  Kemur úr "Deildir" blaðinu í input.json (sjá innlestur.py:lesa_namskeid).
  """
  heiti: str            # Nafn deildar, t.d. "Landspítali Fossvogur"
  vidfang: str           # Viðfangsnúmer deildar í MRS-kerfi Landspítalans (fyrir endurinnflutning)
  plass: int              # Hámarksfjöldi nemenda sem deildin tekur þessa viku
  stadur: str              # Staðsetning (bær/svæði) - notað fyrir "sami staður"/"ekki sami staður" óskir
  hofudborgarsvaedi: bool   # Lesið úr gögnum en ekki notað af neinni virkri skorðu í líkaninu í dag
  postnumer: int              # Notað til að reikna fjarlægð frá heimili nemanda (sjá postur.py)
  stjori: str                  # Nafn deildarstjóra (aðeins notað í úttaki, ekki í líkaninu)
  netfang: str                  # Netfang deildar (aðeins notað í úttaki)
  simanumer: str                 # Símanúmer deildar (aðeins notað í úttaki)
