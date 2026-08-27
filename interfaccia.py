"""
interfaccia.py  --  Final Step Bitcoin / Prisma

L'interfaccia sullo schermo: menu, inserimento delle parole con
autocompletamento, scelta dell'ultima parola.

Gira solo sul dispositivo (MicroPython).

COMANDI
    joystick            si muove fra lettere, voci di menu, elenchi
    A                   conferma / scegli
    B                   cancella / torna indietro
    X e Y               i valori 1 e 0 quando si inseriscono i bit

NIENTE VIENE SALVATO. Le parole restano solo nella memoria di lavoro e
spariscono togliendo corrente.

REGOLA DI DISEGNO: nessuna scritta deve mai uscire dallo schermo. Per
questo NON si scrive mai direttamente, si passa sempre da _testo() o
_centrata(), che rimpiccioliscono da sole finche' il testo ci sta.
"""

import gc
import time

import bip39_checksum as bip39
import diceware as dw
import schermo as s

VERSIONE = "1.0"

DA_INSERIRE = {12: 11, 24: 23}
# bit di entropia liberi nell'ultima parola: sono questi a generare
# le 128 (o 8) candidate valide
BIT_LIBERI = {12: 7, 24: 3}

MARGINE = 6


class Interfaccia:

    SOGLIA_ELENCO = 5
    COLONNE = 5

    def __init__(self):
        self.sc = s.Schermo()
        self.cm = s.Comandi()

    # ------------------------------------------------------------------
    # disegno del testo: sempre dentro lo schermo
    # ------------------------------------------------------------------

    def _scala_che_ci_sta(self, testo, larghezza, scala_max):
        """La scala piu' grande con cui 'testo' ci sta in 'larghezza'."""
        for scala in range(scala_max, 0, -1):
            if len(testo) * 8 * scala <= larghezza:
                return scala
        return 1

    def _testo(self, testo, x, y, c=s.BIANCO, scala=1):
        """
        Scrive RIMPICCIOLENDO finche' il testo ci sta. Non tronca mai.

        Troncare in silenzio e' il peggio: "Ultima parola" diventava
        "Ultima parol" e nessuno capiva perche' mancasse una lettera.
        Meglio un carattere piu' piccolo ma la parola intera.
        """
        if not testo:
            return
        scala = self._scala_che_ci_sta(testo, 240 - x - MARGINE, scala)
        self.sc.scritta(testo, x, y, c, scala)

    def _centrata(self, testo, y, c=s.BIANCO, scala_max=2):
        if not testo:
            return
        scala = self._scala_che_ci_sta(testo, 240 - 2 * MARGINE, scala_max)
        x = max(MARGINE, (240 - len(testo) * 8 * scala) // 2)
        self.sc.scritta(testo, x, y, c, scala)

    def _intestazione(self, testo):
        self.sc.pulisci(s.NERO)
        self._centrata(testo, 6, s.GRIGIO, 2)
        self.sc.hline(0, 28, 240, s.colore(60, 60, 60))

    def _piede(self, sinistra="", destra=""):
        """
        La riga in basso coi comandi. Le due scritte usano SEMPRE la stessa
        dimensione: due misure diverse sulla stessa riga si leggono male.
        Si sceglie la piu' grande che le fa stare entrambe, con uno spazio
        in mezzo perche' non si tocchino.
        """
        self.sc.hline(0, 206, 240, s.colore(60, 60, 60))
        DISTANZA = 4
        posto = 240 - 2 * MARGINE - DISTANZA
        scala = self._scala_che_ci_sta(sinistra + destra, posto, 2)
        if sinistra:
            self.sc.scritta(sinistra, MARGINE, 214 if scala == 2 else 218,
                            s.GRIGIO, scala)
        if destra:
            x = 240 - MARGINE - len(destra) * 8 * scala
            self.sc.scritta(destra, x, 214 if scala == 2 else 218,
                            s.GRIGIO, scala)

    def _messaggio(self, righe, c=s.BIANCO, attesa=True):
        """
        Tutte le righe con LA STESSA dimensione, la piu' grande possibile:
        un messaggio con misure diverse si legge male e sembra sbagliato.
        """
        vere = [r for r in righe if r]
        scala = 3
        for r in vere:
            scala = min(scala, self._scala_che_ci_sta(r, 240 - 2 * MARGINE, 3))

        self.sc.pulisci(s.NERO)
        passo = 10 * scala + 8
        y = 100 - (len(righe) * passo) // 2
        for r in righe:
            if r:
                x = max(MARGINE, (240 - len(r) * 8 * scala) // 2)
                self.sc.scritta(r, x, y, c, scala)
            y += passo
        if attesa:
            self._piede("A) avanti")
        self.sc.mostra()
        if attesa:
            while self.cm.attendi() not in ("A", "centro"):
                pass

    def _barra(self, percento, testo="calcolo"):
        self.sc.pulisci(s.NERO)
        self._centrata(testo, 70, s.BIANCO, 2)
        self.sc.rect(20, 110, 200, 26, s.GRIGIO)
        self.sc.fill_rect(23, 113, int(194 * percento / 100), 20, s.ARANCIO)
        self._centrata("%d%%" % percento, 150, s.GRIGIO, 2)
        self.sc.mostra()

    # ------------------------------------------------------------------
    # menu
    # ------------------------------------------------------------------

    def menu(self, titolo, voci, piede="A) scegli", sotto=None):
        scelta = 0
        while True:
            self._intestazione(titolo)
            y = 46
            for i, v in enumerate(voci):
                if i == scelta:
                    self.sc.fill_rect(4, y - 6, 232, 34, s.colore(45, 32, 0))
                    self._testo(">", 8, y, s.ARANCIO, 2)
                self._testo(v, 26, y, s.ARANCIO if i == scelta else s.BIANCO, 2)
                y += 42
            if sotto and sotto[scelta]:
                # la spiegazione puo' essere una riga sola (piccola) oppure
                # piu' righe corte, che restano a caratteri grandi
                voce = sotto[scelta]
                if isinstance(voce, str):
                    self._centrata(voce, 182, s.GRIGIO, 1)
                else:
                    yy = 200 - len(voce) * 22
                    for riga in voce:
                        self._centrata(riga, yy, s.GIALLO, 2)
                        yy += 22
            self._piede(piede)
            self.sc.mostra()

            t = self.cm.attendi()
            if t == "su":
                scelta = (scelta - 1) % len(voci)
            elif t == "giu":
                scelta = (scelta + 1) % len(voci)
            elif t in ("A", "centro"):
                return scelta
            elif t == "B":
                return None

    # ------------------------------------------------------------------
    # inserimento di UNA parola
    # ------------------------------------------------------------------

    def chiedi_parola(self, numero, totale):
        prefisso = ""
        sel = 0
        calcolato_per = None
        lettere = candidate = None

        while True:
            if prefisso != calcolato_per:
                calcolato_per = prefisso
                candidate = bip39.completa(prefisso) if prefisso else None
                lettere = bip39.lettere_possibili(prefisso)

            # poche parole rimaste: si sceglie direttamente quella giusta
            if candidate is not None and len(candidate) <= self.SOGLIA_ELENCO:
                sel = sel % len(candidate)
                self._intestazione("PAROLA %d/%d" % (numero, totale))
                self._centrata(prefisso, 36, s.GRIGIO, 2)
                y = 66
                for i, p in enumerate(candidate):
                    if i == sel:
                        self.sc.fill_rect(4, y - 5, 232, 30, s.colore(45, 32, 0))
                        self._testo(">", 8, y, s.ARANCIO, 2)
                    self._testo(p, 30, y, s.ARANCIO if i == sel else s.BIANCO, 2)
                    y += 28
                self._piede("A) ok", "B) canc")
                self.sc.mostra()

                t = self.cm.attendi()
                if t == "su":
                    sel = (sel - 1) % len(candidate)
                elif t == "giu":
                    sel = (sel + 1) % len(candidate)
                elif t in ("A", "centro"):
                    return candidate[sel]
                elif t in ("B", "sinistra"):
                    prefisso = prefisso[:-1]
                    sel = 0
                continue

            # griglia delle lettere ancora possibili
            if not lettere:
                prefisso = prefisso[:-1]
                sel = 0
                continue
            sel = sel % len(lettere)
            righe = (len(lettere) + self.COLONNE - 1) // self.COLONNE

            self._intestazione("PAROLA %d/%d" % (numero, totale))
            self._centrata((prefisso + "_") if prefisso else "_", 34, s.ARANCIO, 2)

            LARG, ALT, Y0 = 46, 30, 62
            X0 = (240 - self.COLONNE * LARG) // 2
            for i, L in enumerate(lettere):
                r, c = i // self.COLONNE, i % self.COLONNE
                x, y = X0 + c * LARG, Y0 + r * ALT
                if i == sel:
                    self.sc.fill_rect(x, y, LARG - 2, ALT - 2, s.ARANCIO)
                    self.sc.scritta(L, x + 15, y + 7, s.NERO, 2)
                else:
                    self.sc.scritta(L, x + 15, y + 7, s.BIANCO, 2)

            if prefisso:
                self._centrata("%d parole" % len(candidate),
                               Y0 + righe * ALT + 6, s.GRIGIO, 1)
            self._piede("A) ok", "B) canc")
            self.sc.mostra()

            t = self.cm.attendi()
            r, c = sel // self.COLONNE, sel % self.COLONNE
            if t == "su":
                sel = ((r - 1) % righe) * self.COLONNE + c
            elif t == "giu":
                sel = ((r + 1) % righe) * self.COLONNE + c
            elif t == "sinistra":
                sel = sel - 1 if sel > 0 else len(lettere) - 1
            elif t == "destra":
                sel = sel + 1 if sel < len(lettere) - 1 else 0
            elif t in ("A", "centro"):
                prefisso += lettere[sel]
                sel = 0
            elif t == "B":
                if not prefisso:
                    return None
                prefisso = prefisso[:-1]
                sel = 0
            if sel >= len(lettere):
                sel = len(lettere) - 1

    # ------------------------------------------------------------------
    # l'ultima parola: i bit che mancano
    # ------------------------------------------------------------------

    def chiedi_bit(self, quanti):
        """
        Raccoglie i bit di entropia che mancano all'ultima parola.

        CHI HA GENERATO IL SEED COI DADI QUESTI BIT CE LI HA GIA'.
        Un seed da 12 parole nasce da 128 bit: 121 diventano le prime
        undici parole, e ne AVANZANO 7. Da 24 parole: 256 bit, 253 per le
        prime ventitre, ne avanzano 3. Sono quelli, e vanno inseriti
        nell'ordine in cui sono stati generati (il primo a sinistra).

        Chi invece le parole le ha prese da altrove quei bit non li ha mai
        avuti: allora li tira col lancio di una moneta, ed e' per questo che
        i due pulsanti riportano anche testa e croce.

        Un pulsante per valore: una pressione per bit, niente da scorrere.
        """
        bit = []
        while True:
            self._intestazione("BIT %d/%d" % (min(len(bit) + 1, quanti), quanti))
            self._centrata("i bit che ti avanzano", 34, s.BIANCO, 1)

            # Solo il valore e il pulsante: niente "testa"/"croce".
            # I bit possono arrivare da una moneta, dai dadi o da qualsiasi
            # altra fonte, e nominare una sola di queste sbilancerebbe.
            AZZURRO = s.colore(90, 130, 255)
            self.sc.fill_rect(18, 54, 96, 66, s.colore(0, 55, 0))
            self.sc.rect(18, 54, 96, 66, s.VERDE)
            self._testo("1", 56, 60, s.VERDE, 3)
            self._testo("X", 60, 98, s.VERDE, 2)

            self.sc.fill_rect(126, 54, 96, 66, s.colore(0, 0, 65))
            self.sc.rect(126, 54, 96, 66, AZZURRO)
            self._testo("0", 164, 60, AZZURRO, 3)
            self._testo("Y", 168, 98, AZZURRO, 2)

            uscite = "".join(str(b) for b in bit)
            self._centrata(uscite + "_" * (quanti - len(bit)), 134, s.ARANCIO, 2)
            self._centrata("%d di %d" % (len(bit), quanti), 170, s.GRIGIO, 1)
            self._piede("B) canc")
            self.sc.mostra()

            t = self.cm.attendi()
            if t == "X":
                bit.append(1)
            elif t == "Y":
                bit.append(0)
            elif t == "B":
                if not bit:
                    return None
                bit.pop()
            if len(bit) == quanti:
                valore = 0
                for b in bit:
                    valore = (valore << 1) | b
                return valore

    def scegli_dall_elenco(self, valide):
        """
        Elenco completo delle candidate, con filtro per iniziale: con 128
        parole scorrere e' inutile, filtrando si scende subito a poche.
        """
        filtro = ""
        cima = 0
        sel = 0
        PER_SCHERMO = 5

        while True:
            mostrate = [p for p in valide if p.startswith(filtro)] if filtro else valide
            if not mostrate:
                filtro = ""
                continue
            sel = min(sel, len(mostrate) - 1)
            if sel < cima:
                cima = sel
            elif sel >= cima + PER_SCHERMO:
                cima = sel - PER_SCHERMO + 1

            self._intestazione("%d VALIDE" % len(mostrate))
            if filtro:
                self._testo("filtro: " + filtro, MARGINE, 34, s.ARANCIO, 1)
            y = 50
            for i in range(cima, min(cima + PER_SCHERMO, len(mostrate))):
                if i == sel:
                    self.sc.fill_rect(4, y - 5, 232, 30, s.colore(45, 32, 0))
                    self._testo(">", 8, y, s.ARANCIO, 2)
                self._testo(mostrate[i], 30, y, s.ARANCIO if i == sel else s.BIANCO, 2)
                y += 30
            self._piede("A) ok", "X) filtra")
            self.sc.mostra()

            t = self.cm.attendi()
            if t == "su":
                sel = (sel - 1) % len(mostrate)
            elif t == "giu":
                sel = (sel + 1) % len(mostrate)
            elif t == "sinistra":
                sel = max(0, sel - PER_SCHERMO)
            elif t == "destra":
                sel = min(len(mostrate) - 1, sel + PER_SCHERMO)
            elif t == "X":
                iniziali = []
                for p in valide:
                    if p[0] not in iniziali:
                        iniziali.append(p[0])
                scelto = self._scegli_lettera(iniziali)
                filtro = scelto or ""
                sel = cima = 0
            elif t == "B":
                if filtro:
                    filtro = ""
                    sel = cima = 0
                else:
                    return None
            elif t in ("A", "centro"):
                return mostrate[sel]

    def _scegli_lettera(self, lettere):
        sel = 0
        righe = (len(lettere) + self.COLONNE - 1) // self.COLONNE
        while True:
            self._intestazione("INIZIALE")
            LARG, ALT, Y0 = 46, 34, 60
            X0 = (240 - self.COLONNE * LARG) // 2
            for i, L in enumerate(lettere):
                r, c = i // self.COLONNE, i % self.COLONNE
                x, y = X0 + c * LARG, Y0 + r * ALT
                if i == sel:
                    self.sc.fill_rect(x, y, LARG - 2, ALT - 2, s.ARANCIO)
                    self.sc.scritta(L, x + 15, y + 9, s.NERO, 2)
                else:
                    self.sc.scritta(L, x + 15, y + 9, s.BIANCO, 2)
            self._piede("A) ok", "B) tutte")
            self.sc.mostra()
            t = self.cm.attendi()
            r, c = sel // self.COLONNE, sel % self.COLONNE
            if t == "su":
                sel = ((r - 1) % righe) * self.COLONNE + c
            elif t == "giu":
                sel = ((r + 1) % righe) * self.COLONNE + c
            elif t == "sinistra":
                sel = sel - 1 if sel > 0 else len(lettere) - 1
            elif t == "destra":
                sel = sel + 1 if sel < len(lettere) - 1 else 0
            elif t in ("A", "centro"):
                return lettere[sel]
            elif t == "B":
                return None
            if sel >= len(lettere):
                sel = len(lettere) - 1

    def ultima_parola(self, valide, bit_liberi):
        """
        Come SeedSigner: non si sceglie fra 128 parole, si forniscono i bit
        di entropia che mancano. Le candidate sono ordinate, quindi il
        numero uscito dai lanci e' direttamente la posizione nell'elenco.
        """
        while True:
            scelta = self.menu(
                "ULTIMA PAROLA",
                ["Bit rimasti", "Scegli tu", "Tutti zeri"],
                "A) scegli",
                ["i %d bit avanzati dai dadi" % bit_liberi,
                 "se la conosci gia'",
                 "butta via %d bit di entropia" % bit_liberi])
            if scelta is None:
                return None

            if scelta == 0:
                v = self.chiedi_bit(bit_liberi)
                if v is None:
                    continue
                return valide[v]
            if scelta == 1:
                p = self.scegli_dall_elenco(valide)
                if p is None:
                    continue
                return p
            return valide[0]

    # ------------------------------------------------------------------
    # modalita' completa
    # ------------------------------------------------------------------

    def rivedi_parole(self, parole):
        """
        Elenco numerato delle parole appena inserite, PRIMA di calcolare
        il checksum.

        E' l'unico momento in cui ci si puo' accorgere di aver scelto la
        parola sbagliata dall'autocompletamento: qualunque parola esista
        nel dizionario BIP39 produce comunque 128 (o 8) candidate valide,
        senza nessun errore - il calcolo non puo' distinguere "la parola
        giusta" da "una parola del dizionario, ma quella sbagliata". Senza
        questa schermata, un errore di selezione passa inosservato fino
        alla fine, e il seed completato e' semplicemente diverso da quello
        vero, senza nessun avviso.

        Restituisce True per procedere, False per rifare l'inserimento
        da capo (il tasto "B) rifai" - qui non si corregge una parola
        sola, si ricomincia tutto: piu' semplice da scrivere e da capire,
        a costo di dover ridigitare anche le parole gia' giuste).
        """
        n_pagine = (len(parole) + 9) // 10
        pagina = 0
        while True:
            self._intestazione("CONTROLLA LE PAROLE")
            inizio = pagina * 10
            y = 38
            for i, p in enumerate(parole[inizio:inizio + 10], start=inizio):
                self.sc.scritta("%2d" % (i + 1), 8, y, s.GRIGIO, 1)
                self.sc.scritta(p, 34, y, s.BIANCO, 1)
                y += 16

            # stesso principio delle frecce di mostra_passphrase: nel
            # margine vuoto ai lati delle righe, non sopra
            if n_pagine > 1 and pagina > 0:
                self.sc.scritta("<", 0, 100, s.ARANCIO, 1)
            if n_pagine > 1 and pagina < n_pagine - 1:
                self.sc.scritta(">", 230, 100, s.ARANCIO, 1)

            self._piede("A) avanti", "B) rifai")
            self.sc.mostra()

            t = self.cm.attendi()
            if t in ("A", "centro"):
                return True
            if t == "B":
                return False
            if n_pagine > 1 and t == "destra" and pagina < n_pagine - 1:
                pagina += 1
            elif n_pagine > 1 and t == "sinistra" and pagina > 0:
                pagina -= 1

    def modalita_seed(self):
        scelta = self.menu("QUANTE PAROLE", ["12 parole", "24 parole"])
        if scelta is None:
            return
        totale = 12 if scelta == 0 else 24
        da_inserire = DA_INSERIRE[totale]
        bit_liberi = BIT_LIBERI[totale]

        while True:
            self._messaggio(["INSERISCI", "LE PRIME", "%d PAROLE" % da_inserire])

            parole = []
            while len(parole) < da_inserire:
                p = self.chiedi_parola(len(parole) + 1, da_inserire)
                if p is None:
                    if parole:
                        parole.pop()
                        continue
                    return
                parole.append(p)

            if self.rivedi_parole(parole):
                break
            bip39.dimentica(parole)

        gc.collect()
        self._barra(0)
        valide = bip39.ultime_parole_valide(parole, avanzamento=self._barra)

        finale = self.ultima_parola(valide, bit_liberi)
        if finale is None:
            bip39.dimentica(parole, valide)
            return

        # la parola, grande e da sola: e' quella che va copiata a mano
        self.sc.pulisci(s.NERO)
        self._centrata("PAROLA %d" % totale, 24, s.GRIGIO, 2)
        self.sc.hline(0, 52, 240, s.colore(60, 60, 60))
        self._centrata(finale, 100, s.VERDE, 3)
        self._centrata("scrivila e controlla", 158, s.GRIGIO, 1)
        self._piede("A) avanti")
        self.sc.mostra()
        while self.cm.attendi() not in ("A", "centro"):
            pass

        bip39.dimentica(parole, valide)
        gc.collect()
        self.schermata_finale()

    # ------------------------------------------------------------------
    # passphrase col metodo Diceware
    # ------------------------------------------------------------------

    # un comando per faccia del dado: una pressione per tiro, niente da
    # scorrere. Le quattro direzioni piu' il centro fanno 1-5, la X fa 6.
    DADI_COMANDI = {"su": 1, "destra": 2, "giu": 3, "sinistra": 4,
                    "centro": 5, "X": 6}

    def chiedi_dadi(self, numero):
        """Un tiro: cinque cifre da 1 a 6. None se si annulla."""
        cifre = ""
        while True:
            self._intestazione("PAROLA %d" % numero)
            self._centrata("tira %d dadi" % dw.DADI, 32, s.BIANCO, 1)

            # la crocetta del joystick, coi numeri al posto giusto
            cx, cy, p = 120, 96, 34
            for etichetta, dx, dy in (("1", 0, -1), ("2", 1, 0),
                                      ("3", 0, 1), ("4", -1, 0), ("5", 0, 0)):
                x, y = cx + dx * p - 13, cy + dy * p - 13
                self.sc.rect(x, y, 26, 26, s.GRIGIO)
                self.sc.scritta(etichetta, x + 5, y + 5, s.ARANCIO, 2)
            self.sc.fill_rect(cx + 62, cy - 13, 26, 26, s.colore(45, 32, 0))
            self.sc.rect(cx + 62, cy - 13, 26, 26, s.ARANCIO)
            self.sc.scritta("6", cx + 67, cy - 8, s.ARANCIO, 2)
            self._testo("X", cx + 68, cy + 16, s.GRIGIO, 1)

            self._centrata(cifre + "_" * (dw.DADI - len(cifre)), 158, s.ARANCIO, 3)
            self._piede("B) canc")
            self.sc.mostra()

            t = self.cm.attendi()
            if t in self.DADI_COMANDI:
                cifre += str(self.DADI_COMANDI[t])
                if len(cifre) == dw.DADI:
                    return cifre
            elif t == "B":
                if not cifre:
                    return None
                cifre = cifre[:-1]

    def mostra_passphrase(self, parole):
        """
        L'elenco numerato.

        Fino a dieci parole: tutte su una schermata sola, senza scorrimento -
        fino a sette si scrive grande, da otto a dieci un po' piu' piccolo ma
        ci stanno tutte. Oltre le dieci (fino al massimo di venti) la lista
        si spezza in due schermate da dieci: una freccia nel margine (stesso
        segno usato in mostra_unita) indica che ce n'e' un'altra, destra e
        sinistra ci si passa. La numerazione continua da una schermata
        all'altra, non riparte da 1.
        """
        paginato = len(parole) > 10
        grande = (not paginato) and len(parole) <= 7
        scala = 2 if grande else 1
        passo = 23 if grande else 16
        n_pagine = 2 if paginato else 1
        pagina = 0

        while True:
            self._intestazione("LE TUE PAROLE")
            inizio = pagina * 10
            y = 38
            for i, p in enumerate(parole[inizio:inizio + 10], start=inizio):
                self.sc.scritta("%2d" % (i + 1), 8, y + (3 if grande else 0),
                                s.GRIGIO, 1)
                self.sc.scritta(p, 34, y, s.BIANCO, scala)
                y += passo

            # le frecce stanno nel margine vuoto a fianco delle righe, non
            # sopra: cosi' non tolgono spazio verticale, che con dieci righe
            # e' gia' tutto occupato
            if paginato and pagina > 0:
                self.sc.scritta("<", 0, 100, s.ARANCIO, 1)
            if paginato and pagina < n_pagine - 1:
                self.sc.scritta(">", 230, 100, s.ARANCIO, 1)

            self._centrata("%d parole   %s bit"
                           % (len(parole), dw.bit_testo(len(parole))),
                           192, s.ARANCIO, 1)
            self._piede("A) avanti")
            self.sc.mostra()

            t = self.cm.attendi()
            if t in ("A", "centro"):
                return
            if paginato and t == "destra" and pagina < n_pagine - 1:
                pagina += 1
            elif paginato and t == "sinistra" and pagina > 0:
                pagina -= 1

    def mostra_unita(self, parole):
        """
        La passphrase come una riga sola, da scorrere col joystick.

        Serve a vedere ESATTAMENTE la stringa da digitare, spazi compresi:
        l'elenco numerato dice quali sono le parole, questa dice com'e'
        fatta la passphrase per davvero.
        """
        # CON UNO SPAZIO fra le parole: e' questa la stringa da digitare,
        # carattere per carattere, spazi compresi. Senza uno spazio a
        # separarle la stringa non sarebbe univoca - alcune voci delle
        # liste Diceware sono l'inizio di altre voci (es. "a" e "aa"), quindi
        # tiri di dadi diversi potrebbero incollarsi nella stessa identica
        # passphrase. Lo spazio e' quello che lo impedisce.
        # L'elenco numerato della schermata prima serve solo a controllare
        # di non aver saltato una parola.
        testo = " ".join(parole)
        FINESTRA = 14          # quanti caratteri grandi ci stanno
        pos = 0
        massimo = max(0, len(testo) - FINESTRA)

        while True:
            self._intestazione("LA PASSPHRASE")
            self._centrata("%d caratteri, CON gli spazi" % len(testo), 40, s.GRIGIO, 1)

            pezzo = testo[pos:pos + FINESTRA]
            self.sc.fill_rect(0, 90, 240, 44, s.colore(20, 20, 20))
            self.sc.scritta(pezzo, MARGINE, 102, s.VERDE, 2)

            # frecce: indicano da che parte c'e' ancora testo
            if pos > 0:
                self.sc.scritta("<", 4, 142, s.ARANCIO, 2)
            if pos < massimo:
                self.sc.scritta(">", 220, 142, s.ARANCIO, 2)

            # barretta che mostra a che punto sei
            if massimo:
                largh = max(20, int(228 * FINESTRA / len(testo)))
                self.sc.rect(6, 170, 228, 10, s.GRIGIO)
                self.sc.fill_rect(6 + int((228 - largh) * pos / massimo), 172,
                                  largh, 6, s.ARANCIO)
                self._centrata("joystick per scorrere", 190, s.GRIGIO, 1)

            self._piede("A) fine")
            self.sc.mostra()

            t = self.cm.attendi()
            if t == "destra":
                pos = min(massimo, pos + 1)
            elif t == "sinistra":
                pos = max(0, pos - 1)
            elif t == "giu":
                pos = min(massimo, pos + FINESTRA)
            elif t == "su":
                pos = max(0, pos - FINESTRA)
            elif t in ("A", "centro"):
                return

    def modalita_diceware(self):
        scelta = self.menu("QUALE LISTA", ["Inglese", "Italiano"], "A) scegli",
                           ["Reinhold, 7776 voci", "Gamberini, 7776 voci"])
        if scelta is None:
            return
        # Caricare una lista richiede un blocco di memoria continuo di
        # una cinquantina di KB. Dopo operazioni pesanti la memoria puo'
        # essere frammentata: in quel caso l'unica cosa che rimette tutto
        # a posto e' spegnere e riaccendere, e va detto chiaramente invece
        # di mostrare un errore incomprensibile.
        gc.collect()
        gc.collect()
        try:
            lista = dw.Lista("en" if scelta == 0 else "it")
        except MemoryError:
            self._messaggio(["MEMORIA", "PIENA", "", "SPEGNI E", "RIACCENDI"], s.GIALLO)
            return
        except Exception:
            self._messaggio(["LISTA", "NON", "CARICATA"], s.ROSSO)
            return

        self._messaggio(["TIRA", "5 DADI", "PER PAROLA"])

        # UN SOLO CICLO per tutto: prima c'erano due funzioni quasi uguali
        # e il controllo sul numero minimo di parole stava solo nella prima.
        # Chi rifiutava l'avviso e poi si fermava di nuovo sotto le sei
        # parole non veniva piu' avvisato. Duplicare la logica e' stato
        # l'errore: cosi' il controllo e' in un punto solo e non puo'
        # sfuggire.
        parole = []
        while True:
            if len(parole) >= dw.MASSIMO_PAROLE:
                break

            cifre = self.chiedi_dadi(len(parole) + 1)
            if cifre is None:
                if parole:
                    parole.pop()
                    continue
                return
            p = lista.parola(cifre)
            parole.append(p)

            abbastanza = len(parole) >= dw.CONSIGLIATE
            # al massimo, "A) piu" premere A chiuderebbe comunque la
            # sessione (il controllo all'inizio del ciclo lo impedisce): il
            # tasto va rietichettato, non lasciato a promettere un'undicesima
            # parola che non arriva mai. "B) canc" c'e' sempre, anche sotto
            # il massimo: prima l'unico modo di correggere l'ultima parola
            # era premere A e poi B nella schermata dei dadi successiva,
            # un giro inutile - e al massimo quel giro non era nemmeno
            # disponibile, perche' non c'e' "una parola successiva".
            al_massimo = len(parole) >= dw.MASSIMO_PAROLE
            self.sc.pulisci(s.NERO)
            self._centrata(cifre, 18, s.GRIGIO, 2)
            self._centrata(p, 64, s.VERDE, 3)
            if lista.voce_strana(p):
                self._centrata("copiala esatta!", 112, s.GIALLO, 1)
            self._centrata("%d parole" % len(parole), 136, s.BIANCO, 2)
            self._centrata("%s bit" % dw.bit_testo(len(parole)), 166,
                           s.ARANCIO if abbastanza else s.GIALLO, 2)
            if al_massimo:
                self._piede("A) fine", "B) canc")
            else:
                self._piede("A) piu  B) canc", "Y) fine")
            self.sc.mostra()

            t = self.cm.attendi()
            while t not in ("A", "centro", "Y", "B"):
                t = self.cm.attendi()
            if t == "B":
                # ritira l'ultima parola e la richiede da capo: stessa
                # schermata dei dadi di sempre, non una speciale
                parole.pop()
                continue
            if t != "Y":
                continue

            # si vuole smettere: se sono poche si avvisa, OGNI VOLTA
            if not abbastanza:
                risposta = self.menu(
                    "TROPPO POCHE",
                    ["Continua", "Basta cosi'"], "A) scegli",
                    [("consigliate", "minimo", "%d parole" % dw.CONSIGLIATE),
                     ("hai %s bit" % dw.bit_testo(len(parole)),
                      "invece di %s" % dw.bit_testo(dw.CONSIGLIATE))])
                if risposta != 1:
                    continue
            break

        if not parole:
            return

        # Prima l'avviso, POI le parole: cosi' l'elenco resta l'ultima cosa
        # sullo schermo mentre lo si ricopia. Al contrario si finiva col
        # dire "rileggila due volte" davanti a una schermata senza parole.
        self._messaggio(["TUTTE LE", "PASSPHRASE", "SONO", "RITENUTE", "VALIDE"],
                        s.GIALLO)
        self._messaggio(["SE SBAGLI A", "SCRIVERLA", "NON RICEVERAI", "ERRORI"],
                        s.GIALLO)
        # Si fanno copiare TUTTE E DUE le cose, perche' proteggono da
        # guasti diversi: l'elenco numerato conserva i confini fra le
        # parole, la riga intera conserva i caratteri esatti da digitare.
        # E messe a confronto si controllano a vicenda: e' l'unica rete
        # possibile per una passphrase, che di suo non ha checksum.
        self._messaggio(["COPIA", "L'ELENCO", "NUMERATO"], s.GIALLO)
        self.mostra_passphrase(parole)
        self._messaggio(["COPIA LA", "PASSPHRASE", "PER INTERO"], s.GIALLO)
        # Lo spazio fra le parole e' parte della passphrase, non un a capo
        # visivo: senza, parole diverse potrebbero incollarsi in modo
        # ambiguo. Va detto qui, esplicitamente, prima di mostrarla.
        self._messaggio(["GLI SPAZI", "FANNO PARTE", "DELLA", "PASSPHRASE"],
                        s.GIALLO)
        self.mostra_unita(parole)

        for i in range(len(parole)):
            parole[i] = "      "
        del parole
        gc.collect()
        self.schermata_finale()

    # ------------------------------------------------------------------
    # l'ultima schermata
    # ------------------------------------------------------------------

    def schermata_finale(self):
        """
        L'ultima schermata: il canale, e basta.

        E' UN VICOLO CIECO DI PROPOSITO. Nessun tasto porta da qualche
        parte: l'unico modo di uscire e' staccare il cavo.

        Non e' una scortesia, e' l'unica cosa che azzera davvero la memoria
        di lavoro. Se da qui si potesse tornare al menu, le parole appena
        generate resterebbero in memoria per tutto il tempo in cui il
        dispositivo resta acceso, e "spegni dopo l'uso" sarebbe solo un
        consiglio che qualcuno prima o poi non segue. Cosi' invece e'
        l'unica strada possibile.

        Il codice QR non viene calcolato qui: e' un'immagine gia' pronta,
        disegnata una volta sola sul computer (vedi prepara_qr.py). Nel
        firmware entrano solo i dati, non la libreria che li produce.
        """
        self.sc.pulisci(s.NERO)
        self._centrata("SEGUIMI!", 6, s.VERDE, 3)

        try:
            import qr_canale as qr
        except Exception:
            qr = None

        if qr:
            PIXEL = 4
            BORDO = 4                       # margine chiaro, lo vuole lo standard
            lato = (qr.LATO + 2 * BORDO) * PIXEL
            x0 = (240 - lato) // 2
            y0 = 34
            # il fondo chiaro: senza, il codice non si legge
            self.sc.fill_rect(x0, y0, lato, lato, s.BIANCO)
            for r in range(qr.LATO):
                riga = qr.MODULI[r]
                y = y0 + (BORDO + r) * PIXEL
                c = 0
                while c < qr.LATO:
                    if riga[c] == "1":
                        # disegno i moduli scuri di fila in un colpo solo
                        fine = c
                        while fine < qr.LATO and riga[fine] == "1":
                            fine += 1
                        self.sc.fill_rect(x0 + (BORDO + c) * PIXEL, y,
                                          (fine - c) * PIXEL, PIXEL, s.NERO)
                        c = fine
                    else:
                        c += 1
        else:
            self._centrata("finalstepbitcoin.com", 110, s.BIANCO, 1)

        self.sc.hline(0, 206, 240, s.colore(60, 60, 60))
        self._centrata("SCOLLEGA", 214, s.VERDE, 2)
        self.sc.mostra()

        # da qui non si esce: nessun tasto fa niente. Vedi la spiegazione
        # in cima alla funzione.
        while True:
            time.sleep_ms(200)

    # ------------------------------------------------------------------

    def benvenuto(self):
        """
        La prima schermata: nome, versione e IMPRONTA DEL FIRMWARE.

        Le tre parole vanno confrontate con quelle stampate sul foglietto
        nella scatola e pubblicate sul sito. Questa schermata ASPETTA una
        pressione invece di sparire da sola: il confronto e' il motivo per
        cui esiste, e va fatto con calma.
        """
        # una schermata di cortesia mentre si calcola: dura un attimo
        self.sc.pulisci(s.NERO)
        self._centrata("FINAL STEP", 92, s.ARANCIO, 2)
        self._centrata("BITCOIN", 120, s.ARANCIO, 2)
        self.sc.mostra()

        bip39.lettere_possibili("")     # prepara la ricerca, costa un secondo
        tre = None
        guasto_memoria = False
        try:
            import impronta
            tre = impronta.parole()
        except MemoryError:
            # distinto dagli altri errori apposta: qui c'e' un rimedio
            # preciso da suggerire (come gia' fa modalita_diceware), non
            # solo un generico "non disponibile" che non dice cosa fare
            guasto_memoria = True
        except Exception:
            tre = None

        self.sc.pulisci(s.NERO)
        self.sc.rect(6, 6, 228, 228, s.colore(60, 40, 0))
        self._centrata("FINAL STEP", 16, s.ARANCIO, 2)
        self._centrata("BITCOIN", 40, s.ARANCIO, 2)
        self.sc.hline(20, 68, 200, s.colore(60, 60, 60))

        if tre:
            self._centrata("impronta firmware", 76, s.GRIGIO, 1)
            y = 96
            for p in tre:
                self._centrata(p.upper(), y, s.VERDE, 2)
                y += 24
        elif guasto_memoria:
            self._centrata("memoria piena", 100, s.GIALLO, 1)
            self._centrata("spegni e riaccendi", 124, s.GIALLO, 1)
        else:
            self._centrata("impronta", 100, s.GRIGIO, 1)
            self._centrata("non disponibile", 124, s.GIALLO, 1)

        self.sc.hline(20, 172, 200, s.colore(60, 60, 60))
        self._centrata("il tuo calcolatore offline", 180, s.BIANCO, 1)
        self._centrata("Prisma " + VERSIONE, 194, s.GRIGIO, 1)
        self._piede("A) avanti")
        self.sc.mostra()
        while self.cm.attendi() not in ("A", "centro"):
            pass

    def avvia(self):
        self.benvenuto()
        while True:
            scelta = self.menu("MENU",
                               ["Checksum", "Passphrase", "Informazioni"],
                               "A) scegli",
                               ["ultima parola BIP39",
                                "passphrase coi dadi",
                                "versione e verifica"])
            if scelta == 0:
                self.modalita_seed()
            elif scelta == 1:
                self.modalita_diceware()
            elif scelta == 2:
                self._messaggio(["Prisma", VERSIONE,
                                 "finalstep", "bitcoin.com"], s.BIANCO)


def avvia():
    """
    Avvia l'interfaccia. Se qualcosa va storto l'errore viene mostrato
    SULLO SCHERMO: senza questa rete un errore lascerebbe l'ultima immagine
    congelata, e sembrerebbe un blocco invece di un guasto.
    """
    i = Interfaccia()
    try:
        i.avvia()
    except Exception as e:
        try:
            import io
            import sys
            f = io.StringIO()
            sys.print_exception(e, f)
            testo = f.getvalue()
        except Exception:
            testo = str(e)
        i.sc.pulisci(s.colore(60, 0, 0))
        i.sc.scritta("ERRORE", 8, 8, s.BIANCO, 2)
        i.sc.hline(0, 34, 240, s.BIANCO)
        y = 44
        for riga in testo.split("\n"):
            riga = riga.strip()
            while riga and y < 214:
                i.sc.scritta(riga[:29], 6, y, s.BIANCO, 1)
                riga = riga[29:]
                y += 12
        i.sc.scritta("stacca e ricollega", 40, 222, s.BIANCO, 1)
        i.sc.mostra()
        raise
