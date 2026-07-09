from dataclasses import dataclass, field
from deild import Deild

@dataclass
class ModelData:
  """Allt sem líkanið (model_generator*.py) þarf til að setja upp og leysa
  röðunarvandamálið, byggt upp af innlestur.py úr input.json.

  Sameiginlegt vísanakerfi sem er notað út um allan kóðann, bæði hér og í
  model_generator*.py/solution_check.py/utkoma.py:
    s = notandanafn eins nemanda (lykill í `nemendur`)
    c = auðkenni eins námskeiðs, klínísks eða valnámskeiðs (lykill í `klinik`)
    v = vikuraðnúmer sem lota/pláss byrjar í (lykill í `klinik[c]`)
    d = heiti einnar deildar (lykill í `klinik[c][v]`, gildið er Deild)

  Þannig vísar `klinik[c][v][d]` á eina Deild - eitt klínískt pláss fyrir
  námskeið c, í viku v, á deild d.
  """

  klinik: dict = field(default_factory=dict)            # klinik[c][v][d] -> Deild (sjá lýsingu að ofan)
  nemendaskraning: dict = field(default_factory=dict)     # nemendaskraning[s][c] -> 1/0, er nemandi s skráð/ur í námskeið c
  nemendur: dict = field(default_factory=dict)              # nemendur[s] -> Nemandi
  val_listi: set = field(default_factory=set)                 # Auðkenni allra valnámskeiða (ekki klínísk)
  val_nemenda: dict = field(default_factory=dict)               # val_nemenda[s][c] -> 1/0, er nemandi s skráð/ur í valnámskeið c
  nemendur_val_vikur: dict = field(default_factory=dict)          # nemendur_val_vikur[s] -> mengi vikna sem nemandi s er í einhverju valnámskeiði
  klinik_vikur: dict = field(default_factory=dict)                  # klinik_vikur[c][v] -> mengi raunverulegra vikna sem lotan sem byrjar í viku v spannar
  val_vikur: dict = field(default_factory=dict)                      # val_vikur[c] -> listi vikna sem valnámskeið c stendur yfir
  vikur: set = field(default_factory=set)                              # Allar vikur sem koma fyrir í stundatöflunni (Lotur)
  klara_snemma: dict = field(default_factory=dict)                      # klara_snemma[s] -> vika sem nemandi s verður að vera búin/n með alla klíník fyrir
  klara_snemma_serstakt: dict = field(default_factory=dict)               # klara_snemma_serstakt[s][c] -> sama, en fyrir eitt tiltekið námskeið
  sama_deild: dict = field(default_factory=dict)                            # sama_deild[s][c] -> mengi deilda sem nemandi s óskar eftir í námskeiði c
  ekki_sama_deild: dict = field(default_factory=dict)                        # ekki_sama_deild[s][c] -> mengi deilda sem nemandi s vill ekki fara á
  sami_stadur: dict = field(default_factory=dict)                              # sami_stadur[s][c] -> mengi staða sem nemandi s óskar eftir
  ekki_sami_stadur: dict = field(default_factory=dict)                          # ekki_sami_stadur[s][c] -> mengi staða sem nemandi s vill ekki fara á
  fri_osk: dict = field(default_factory=dict)                                     # fri_osk[s] -> mengi vikna sem nemandi s óskar eftir fríi í (mjúk ósk)
  fri_skilyrt: dict = field(default_factory=dict)                                  # fri_skilyrt[s] -> mengi vikna sem nemandi s verður að fá frí í (hörð skorða)
  auka_vikur: set = field(default_factory=set)                                       # Neikvæð, tilbúin "yfirfljóts" vikunúmer - sjá generate_extra_weeks

  stadir: dict = field(default_factory=dict)               # stadir[c] -> mengi allra staða sem einhver nemandi hefur óskað eftir fyrir námskeið c
  akvedin_rodun: dict = field(default_factory=dict)          # akvedin_rodun[s][c] -> {'deildir': mengi, 'vikur': mengi} - fyrirfram ákveðin (ekki valfrjáls) röðun

  def generate_extra_weeks(self):
    """Bætir við einu tilbúnu "Vantar pláss" plássi (ótakmörkuðu að stærð) í
    hverju námskeiði, í nýju neikvæðu vikunúmeri. Þetta tryggir að líkanið
    finni alltaf einhverja lausn (aldrei "infeasible"), jafnvel þegar raunveruleg
    pláss duga ekki - markfallið refsar mjög harkalega fyrir að nota þessi
    pláss (sjá vigt_auka_vikur í model_generator*.py), svo þau eru því aðeins
    notuð þegar engin önnur lausn er möguleg, og solution_check.py flaggar
    slíkt sem alvarlega villu svo hægt sé að bregðast við."""
    i = 0
    fjoldi = len(self.nemendur)
    for c in self.klinik:
      i -= 1
      self.klinik[c].update({ i: {'Vantar pláss': Deild(heiti='auka', vidfang='00000', plass=fjoldi, stadur='', hofudborgarsvaedi=True, postnumer=101, stjori='', netfang='', simanumer='113')} })

    self.auka_vikur = set(range(i,0))

  def generate_extra_data(self):
    """Reiknar `stadir[c]` út frá `sami_stadur` - notað í markfallinu til að
    refsa fyrir að setja nemendur á staði sem enginn hefur sérstaklega beðið um."""
    for c in self.klinik:
      self.stadir[c] = set()
    for s in self.sami_stadur:
      for c in self.sami_stadur[s]:
        for d in self.sami_stadur[s][c]:
          try:
            self.stadir[c].add(d)
          except:
            print('................')
            for c in self.stadir:
              print(c)
            print('................')
            raise
