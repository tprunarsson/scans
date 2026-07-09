from dataclasses import dataclass

@dataclass
class Nemandi:
  """Einn nemandi, kemur úr "Nemendur" blaðinu í input.json.

  Auðkennið sem er notað alls staðar annars staðar í líkaninu (breytuvísar,
  skráningar, óskir) er `notandanafn` - það er lykillinn í ModelData.nemendur
  dict-inu, ekki geymt hér sem sérstakt svæði.
  """
  nafn: str          # Fullt nafn, notað í úttaki og villuskilaboðum
  kennitala: str       # Fyllt upp í 10 stafi með núllum að framan
  netfang: str           # Sama gildi og notandanafn (sögulega tvítekið svæði)
  farsimi: str             # Notað í úttaki (mrs_radad_*)
  postnumer: int             # Notað til að reikna fjarlægð til deilda (sjá postur.py)
  olett: int                  # Sögulegt svæði - ekki lesið úr input.json, alltaf 0, ekki notað af líkaninu.
