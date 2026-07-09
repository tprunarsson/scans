class Vikur:
  """Býr til "samhverfa" vikutalningu svo hægt sé að bera saman vikur sem
  liggja beggja vegna áramóta á sama skólaári (skólaárið byrjar um miðbik
  almanaksársins, kringum ISO-viku 25).

  self.sym: ISO-vikunúmer (1-52) -> vikuraðnúmer innan skólaárs (0-51), þar
  sem vika `mid` (25) verður 0 og vikur telja áfram þaðan, með vikum 1-24
  næsta almanaksárs settar aftast (26-51). Þetta gerir t.d. `sym[35] < sym[3]`
  satt, sem er rétt innan skólaársins þó 3 < 35 sem hrá ISO-vikunúmer.

  self.raun: andhverfa self.sym - vikuraðnúmer -> ISO-vikunúmer.
  """
  def __init__(self):
    self.mid = 25
    self.sym = dict()
    for v in range(self.mid, 53):
      self.sym[v] = v - self.mid
    for v in range(1, self.mid):
      self.sym[v] = v + 52 - self.mid

    self.raun = { self.sym[v]: v for v in self.sym }
