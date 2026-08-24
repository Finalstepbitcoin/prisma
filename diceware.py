"""
diceware.py  --  Final Step Bitcoin / Sintesi

Dai numeri dei dadi alle parole della passphrase.

Gira sia sul Mac sia sul dispositivo.

COSA FA
  Cinque dadi a sei facce danno un numero di cinque cifre da 11111 a 66666:
  6^5 = 7776 combinazioni, cioe' esattamente una per ogni voce della lista.
  Nessuno scarto, nessuna combinazione sprecata: ogni parola ha la stessa
  identica probabilita'. E' questo che rende il metodo solido.

COSA NON FA
  Non genera niente. Il caso lo porta l'utente coi dadi, il dispositivo fa
  solo la traduzione - la stessa che si farebbe a mano con la lista
  stampata, solo senza sbagliare riga.

ATTENZIONE, DIFFERENZA IMPORTANTE COL SEED
  Una passphrase NON HA CHECKSUM. Se viene trascritta male non se ne accorge
  nessuno: non compare nessun errore, si entra semplicemente in un altro
  portafoglio, vuoto. Il seed BIP39 invece protegge da questo.
"""

# 12,9248 bit per parola: log in base 2 di 7776.
#
# La tabella qui sotto e' in DECIMI DI BIT. Solo i primi undici valori
# (indici 0-10, cioe' fino a 10 parole) sono gli stessi identici stampati
# sulla scheda di carta "Dai dadi alle parole Diceware" - scritti a mano di
# proposito, cosi' schermo e carta non possono discordare per un
# arrotondamento diverso (il dispositivo gira MicroPython, la scheda si
# genera con Python del Mac: due implementazioni diverse dei numeri a
# virgola mobile potrebbero, in teoria, arrotondare in modo diverso lo
# stesso calcolo dal vivo).
#
# Da 11 a 20 parole (il massimo, oltre le dieci righe di una scheda) i
# valori sono calcolati con la STESSA formula ma non sono stampati da
# nessuna parte: la scheda resta a dieci righe, se ne servono di piu' se
# ne usano due. Chi arriva a quelle parole legge il totale dei bit solo
# qui sullo schermo.
BIT_DECIMI = (0, 129, 258, 388, 517, 646, 775, 905, 1034, 1163, 1292,
              1422, 1551, 1680, 1809, 1939, 2068, 2197, 2326, 2456, 2585)

MASSIMO_PAROLE = 20        # due schermate da dieci parole
CONSIGLIATE = 6            # sotto le sei parole il dispositivo avvisa
DADI = 5


def bit(n_parole):
    """Entropia accumulata, in decimi di bit (per non usare i decimali)."""
    if n_parole < len(BIT_DECIMI):
        return BIT_DECIMI[n_parole]
    return int(round(n_parole * 129.248))


def bit_testo(n_parole):
    """Gli stessi valori della scheda, scritti come sulla carta: '77,5'."""
    d = bit(n_parole)
    return "%d,%d" % (d // 10, d % 10)


class Lista:
    """
    Una lista Diceware. Si carica solo quella scelta, non tutte e due:
    ognuna occupa una quarantina di KB.
    """

    def __init__(self, codice_lingua):
        if codice_lingua == "it":
            import diceware_it as m
        else:
            import diceware_en as m
        self.m = m
        self.nome = m.NOME
        self.autore = m.AUTORE
        self.licenza = m.LICENZA
        self.impronta = m.IMPRONTA

    def indice(self, cifre):
        """
        Dal numero dei dadi alla posizione nella lista.
        'cifre' e' una stringa o una lista di cinque numeri da 1 a 6.
        """
        if len(cifre) != DADI:
            raise ValueError("servono %d dadi, non %d" % (DADI, len(cifre)))
        n = 0
        for c in cifre:
            v = int(c)
            if v < 1 or v > 6:
                raise ValueError("un dado a sei facce non fa %d" % v)
            n = n * 6 + (v - 1)
        return n

    def parola(self, cifre):
        """
        La voce corrispondente al tiro.

        Restituita ESATTAMENTE come sta nella lista: se contiene un
        apostrofo, una & o e' solo una cifra, resta cosi'. Modificarla
        romperebbe la corrispondenza con la lista stampata.
        """
        i = self.indice(cifre)
        L = self.m.LARGHEZZA
        return self.m.BLOB[i * L:(i + 1) * L].rstrip()

    def voce_strana(self, parola):
        """
        True se la voce contiene qualcosa di diverso dalle lettere.
        Serve solo ad avvisare chi la deve trascrivere a mano: simboli,
        apostrofi e cifre sono legittimi ma facili da copiare male.
        """
        return not parola.isalpha()
