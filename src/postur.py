"""Reiknar fjarlægð (í reiknieiningum, ekki endilega km) milli póstnúmera á
Íslandi, notað í markfalli líkansins til að forgangsraða því að setja
nemendur á deildir nálægt heimili þeirra (sjá model_generator*.py).

Fjarlægðir milli beintengdra póstnúmera eru handslegnar inn hér að neðan út
frá raunverulegri vegalengd; Floyd-Warshall er svo keyrt til að reikna
styttstu leið milli allra para, líka þeirra sem eru ekki beintengd."""
import numpy as np

class Postur:
  def __init__(self):
    self.p, self.post_fjar = get_stuff()

  def fjar(self, p1, plist):
    """Meðalfjarlægð frá póstnúmeri p1 til hvers póstnúmers í plist (t.d. ef
    deild er skráð með fleiri en eitt póstnúmer). Skilar 0 ef p1 eða eitthvert
    gildi í plist er ekki þekkt póstnúmer, frekar en að láta forritið hrynja."""
    try:
      return np.mean(np.array([self.post_fjar[self.p[p1], self.p[i]] for i in plist]))
    except:
      return 0

def get_stuff():
  p = {
    101: 0,
    102: 1,
    103: 2,
    104: 3,
    105: 4,
    107: 5,
    108: 6,
    109: 7,
    110: 8,
    111: 9,
    112: 10,
    113: 11,
    116: 12,
    162: 13,
    170: 14,
    200: 15,
    201: 16,
    203: 17,
    210: 18,
    220: 19,
    221: 20,
    225: 21,
    270: 22,
    271: 23
  }

  n = len(p)
  post_fjar = np.zeros((n, n))

  post_fjar[p[101],p[102]] = 2.0
  post_fjar[p[101],p[104]] = 4.4
  post_fjar[p[101],p[105]] = 2.0
  post_fjar[p[101],p[107]] = 1.5


  post_fjar[p[102],p[103]] = 2.5
  post_fjar[p[102],p[105]] = 2.0
  post_fjar[p[102],p[107]] = 2.0
  post_fjar[p[102],p[200]] = 4.2

  post_fjar[p[103],p[105]] = 1.7
  post_fjar[p[103],p[108]] = 1.3
  post_fjar[p[103],p[200]] = 2.5

  post_fjar[p[104],p[105]] = 2.8
  post_fjar[p[104],p[108]] = 2.0
  post_fjar[p[104],p[109]] = 5.0
  post_fjar[p[104],p[110]] = 5.0
  post_fjar[p[104],p[111]] = 5.5
  post_fjar[p[104],p[112]] = 5.9
  post_fjar[p[104],p[113]] = 7.3
  post_fjar[p[104],p[270]] = 12.5

  post_fjar[p[105],p[108]] = 2.5

  post_fjar[p[107],p[170]] = 2.0

  post_fjar[p[108],p[109]] = 3.7
  post_fjar[p[108],p[110]] = 4.5
  post_fjar[p[108],p[111]] = 4.5
  post_fjar[p[108],p[112]] = 5.9
  post_fjar[p[108],p[113]] = 7.0
  post_fjar[p[108],p[200]] = 3.0
  post_fjar[p[108],p[201]] = 4.2
  post_fjar[p[108],p[270]] = 12.0

  post_fjar[p[109],p[110]] = 3.4
  post_fjar[p[109],p[111]] = 1.4
  post_fjar[p[109],p[112]] = 6.7
  post_fjar[p[109],p[200]] = 3.8
  post_fjar[p[109],p[201]] = 1.9
  post_fjar[p[109],p[203]] = 3.5

  post_fjar[p[110],p[111]] = 2.2
  post_fjar[p[110],p[112]] = 4.3
  post_fjar[p[110],p[113]] = 3.1
  post_fjar[p[110],p[200]] = 6.3
  post_fjar[p[110],p[203]] = 4.0
  post_fjar[p[110],p[270]] = 8.6

  post_fjar[p[111],p[112]] = 5.9
  post_fjar[p[111],p[203]] = 2.6

  post_fjar[p[112],p[113]] = 3.5
  post_fjar[p[112],p[270]] = 6.5

  post_fjar[p[113],p[270]] = 6.6
  post_fjar[p[113],p[203]] = 6.5

  post_fjar[p[116],p[162]] = 1.0
  post_fjar[p[116],p[270]] = 15.0
  post_fjar[p[116],p[271]] = 15.0

  post_fjar[p[200],p[201]] = 3.0
  post_fjar[p[200],p[210]] = 4.0
  post_fjar[p[200],p[220]] = 7.0
  post_fjar[p[200],p[221]] = 10.0
  post_fjar[p[200],p[225]] = 8.6

  post_fjar[p[201],p[203]] = 3.4
  post_fjar[p[201],p[210]] = 3.8
  post_fjar[p[201],p[220]] = 6.8
  post_fjar[p[201],p[221]] = 10.0
  post_fjar[p[201],p[225]] = 9.5

  post_fjar[p[203],p[210]] = 6.4
  post_fjar[p[203],p[220]] = 9.0
  post_fjar[p[203],p[221]] = 12.0

  post_fjar[p[210],p[220]] = 3.5
  post_fjar[p[210],p[221]] = 7.1
  post_fjar[p[210],p[225]] = 6.1

  post_fjar[p[220],p[221]] = 3.7
  post_fjar[p[220],p[225]] = 6.0

  post_fjar[p[270],p[271]] = 4.9

  # Samhverfa
  for i in range(n):
    for j in range(n):
      post_fjar[i,j] = max(post_fjar[i,j], post_fjar[j,i])
      if post_fjar[i,j] == 0.0 and i != j:
        # Ekki búið að reikna fjarlægð
        post_fjar[i,j] = 1000000.0

  # Floyd-Warshall
  for k in range(n):
    for i in range(n):
      for j in range(n):
        post_fjar[i,j] = min(post_fjar[i,j], post_fjar[i,k] + post_fjar[k,j])

  return p, post_fjar