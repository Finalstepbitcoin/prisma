"""
prova_percorsi.py  --  Final Step Bitcoin / Sintesi

Ripercorre da solo tutte le strade dell'interfaccia, simulando le pressioni
dei tasti, e controlla che nessuna finisca in errore.

GIRA SUL DISPOSITIVO. Si lancia dal computer con:
    python3 parla_col_pico.py esegui --pulito "import prova_percorsi"

A COSA SERVE
Provare a mano ogni combinazione richiederebbe centinaia di pressioni e
qualcuna sfuggirebbe sempre. Qui invece ogni percorso viene ripercorso
identico a ogni modifica: se qualcosa si rompe, si scopre subito e si sa
esattamente dove.
"""

import gc

import bip39_checksum as bip39
import diceware as dw
import interfaccia

FRASE = ("legal winner thank year wave sausage worth useful "
         "legal winner thank").split()

_esiti = []


def prova(nome, funzione):
    gc.collect()
    try:
        funzione()
        _esiti.append((nome, None))
        print("  ok      %s" % nome)
    except Exception as e:
        _esiti.append((nome, e))
        print("  FALLITO %s  ->  %r" % (nome, e))


def con_tasti(i, tasti):
    """Fa rispondere l'interfaccia a una sequenza di tasti gia' decisa."""
    pos = [0]

    def finto(scadenza_ms=None):
        if pos[0] >= len(tasti):
            raise Exception("sequenza finita: servivano piu' di %d tasti" % len(tasti))
        t = tasti[pos[0]]
        pos[0] += 1
        return t

    i.cm.attendi = finto
    return pos


def tasti_per_parola(i, parola):
    """Le pressioni che servono a inserire una parola col sistema a griglia."""
    fuori = []
    prefisso = ""
    while True:
        candidate = bip39.completa(prefisso) if prefisso else None
        if candidate is not None and len(candidate) <= i.SOGLIA_ELENCO:
            fuori += ["giu"] * candidate.index(parola) + ["A"]
            return fuori
        lettere = bip39.lettere_possibili(prefisso)
        k = lettere.index(parola[len(prefisso)])
        fuori += ["giu"] * (k // i.COLONNE) + ["destra"] * (k % i.COLONNE) + ["A"]
        prefisso += parola[len(prefisso)]


def tasti_per_dadi(i, cifre):
    inverso = {}
    for nome, valore in i.DADI_COMANDI.items():
        inverso[valore] = nome
    return [inverso[int(c)] for c in cifre]


def esegui():
    i = interfaccia.Interfaccia()
    i.schermata_finale = lambda: None      # e' un vicolo cieco: qui lo saltiamo
    bip39.lettere_possibili("")

    valide = bip39.ultime_parole_valide(FRASE)
    parole_seed = []
    for p in FRASE:
        parole_seed += tasti_per_parola(i, p)

    print("\nPERCORSI COMPLETI")

    zero, uno = valide[0], valide[127]

    # Dopo l'ultima parola inserita c'e' ora rivedi_parole (l'elenco da
    # ricontrollare prima del calcolo): un "A" in piu' per accettarlo alla
    # prima pagina, prima di proseguire come prima verso l'ultima parola.
    RIVEDI_ACCETTA = ["A"]

    def seed_bit():
        con_tasti(i, ["A", "A"] + parole_seed + RIVEDI_ACCETTA + ["A"] + ["Y"] * 7 + ["A"])
        i.modalita_seed()
    prova("seed 12 parole, bit tutti a zero -> %s" % zero, seed_bit)

    def seed_uni():
        con_tasti(i, ["A", "A"] + parole_seed + RIVEDI_ACCETTA + ["A"] + ["X"] * 7 + ["A"])
        i.modalita_seed()
    prova("seed 12 parole, bit tutti a uno -> %s" % uno, seed_uni)

    def seed_zeri():
        con_tasti(i, ["A", "A"] + parole_seed + RIVEDI_ACCETTA
                  + ["giu", "giu", "A", "A"])
        i.modalita_seed()
    prova("seed 12 parole, voce 'tutti zeri'", seed_zeri)

    def seed_elenco():
        con_tasti(i, ["A", "A"] + parole_seed + RIVEDI_ACCETTA
                  + ["giu", "A"] + ["giu"] * 3 + ["A", "A"])
        i.modalita_seed()
    prova("seed 12 parole, scelta dall'elenco", seed_elenco)

    def seed_cancella():
        # inserisce due parole, torna indietro con B, le rifa. Non arriva
        # mai a rivedi_parole (esce da modalita_seed prima, quando l'ultimo
        # B svuota l'elenco): nessun tasto in piu' da aggiungere qui.
        due = tasti_per_parola(i, FRASE[0]) + tasti_per_parola(i, FRASE[1])
        con_tasti(i, ["A", "A"] + due + ["B", "B", "B", "B", "B", "B", "B", "B"])
        i.modalita_seed()
    prova("seed, ritorno indietro con B fino a uscire", seed_cancella)

    def seed_rivedi_due_pagine():
        """rivedi_parole con 11 parole sta su due pagine (10+1): qui si va
        alla seconda con la freccia, si rifiuta con B) rifai, si rifa'
        tutto l'inserimento e stavolta si accetta - la stessa distinzione
        gia' provata per Diceware (dadi_annulla, dadi_due_schermate), qui
        per il flusso del seed."""
        seq = (["A", "A"] + parole_seed + ["destra", "B"]
               + ["A"] + parole_seed + ["A"]
               + ["giu", "giu", "A", "A"])
        con_tasti(i, seq)
        i.modalita_seed()
    prova("seed, revisione parole: pagina 2 poi rifai", seed_rivedi_due_pagine)

    print("\nSINGOLE SCHERMATE")

    def bit_sette():
        con_tasti(i, ["X", "Y", "X", "Y", "X", "Y", "X"])
        v = i.chiedi_bit(7)
        assert v == 0b1010101, "letti %d invece di 85" % v
    prova("inserimento di 7 bit -> 85", bit_sette)

    def bit_tre():
        con_tasti(i, ["X", "X", "X"])
        assert i.chiedi_bit(3) == 7
    prova("inserimento di 3 bit -> 7", bit_tre)

    def bit_cancella():
        con_tasti(i, ["X", "X", "B", "Y", "Y", "Y", "Y", "Y", "Y"])
        assert i.chiedi_bit(7) == 0b1000000
    prova("inserimento bit con cancellazione", bit_cancella)

    def elenco_filtrato():
        con_tasti(i, ["X", "A", "A"])       # filtra per iniziale, poi sceglie
        p = i.scegli_dall_elenco(valide)
        assert p in valide, "scelta fuori elenco: %s" % p
    prova("elenco candidate col filtro per iniziale", elenco_filtrato)

    def ultima_zeri():
        con_tasti(i, ["giu", "giu", "A"])
        assert i.ultima_parola(valide, 7) == valide[0]
    prova("ultima parola con 'tutti zeri'", ultima_zeri)

    # Liberiamo tutto quello che serviva ai percorsi del seed: le 128
    # parole e le sequenze di tasti pesano, e nell'uso vero non restano
    # mai in vita mentre si carica una lista Diceware.
    del valide, parole_seed
    gc.collect()

    print("\nMODALITA' DADI")

    # Le schermate da confermare con A DOPO che si e' deciso di fermarsi:
    # TUTTE LE PASSPHRASE, SE SBAGLI A SCRIVERLA, COPIA L'ELENCO NUMERATO,
    # l'elenco stesso (mostra_passphrase), COPIA LA PASSPHRASE PER INTERO,
    # GLI SPAZI FANNO PARTE, la passphrase intera (mostra_unita). Un unico
    # numero con nome invece che ripetuto a mano in ogni prova: e' proprio
    # perche' era ripetuto a mano che l'aggiunta di "GLI SPAZI FANNO PARTE"
    # (issue #3) aveva lasciato queste prove indietro di una schermata
    # senza che nessuno se ne accorgesse, finche' non si sono rilanciate
    # per davvero sul dispositivo.
    SCHERMATE_FINALI = 7

    for lingua, indice in (("inglese", 0), ("italiano", 1)):
        def dadi(indice=indice):
            lista = dw.Lista("en" if indice == 0 else "it")
            tiri = ["52431", "11111", "66666", "34251", "16234", "44444"]
            seq = ["A"] * (indice + 1) + ["A"]
            if indice:
                seq = ["giu", "A", "A"]
            for n, t in enumerate(tiri):
                seq += tasti_per_dadi(i, t)
                seq.append("Y" if n == len(tiri) - 1 else "A")
            seq += ["A"] * SCHERMATE_FINALI
            con_tasti(i, seq)
            i.modalita_diceware()
            del lista
        prova("dadi, lista %s, 6 parole" % lingua, dadi)

    def dadi_avviso():
        seq = ["A", "A"]
        for t in ("11111", "22222", "33333"):
            seq += tasti_per_dadi(i, t) + ["A"]
        seq[-1] = "Y"
        seq += ["A"]                                  # "Continua"
        seq += tasti_per_dadi(i, "44444") + ["Y"]     # secondo avviso
        seq += ["giu", "A"]                           # "Basta cosi'"
        seq += ["A"] * SCHERMATE_FINALI
        con_tasti(i, seq)
        i.modalita_diceware()
    prova("dadi, avviso ripetuto sotto le 6 parole", dadi_avviso)

    def dadi_esce():
        con_tasti(i, ["A", "A", "B"])
        i.modalita_diceware()
    prova("dadi, uscita subito con B", dadi_esce)

    def dadi_annulla():
        """Il tasto B) canc sulla schermata di conferma (non quello dentro
        chiedi_dadi, gia' provato da dadi_esce): tira 3 parole, alla terza
        si annulla e la ritira, poi si ferma con l'avviso sotto le 6."""
        seq = ["A", "A"]
        seq += tasti_per_dadi(i, "11111") + ["A"]      # parola 1
        seq += tasti_per_dadi(i, "22222") + ["A"]      # parola 2
        seq += tasti_per_dadi(i, "33333") + ["B"]      # parola 3, ripensata...
        seq += tasti_per_dadi(i, "44444") + ["Y"]      # ...ritirata, e si ferma qui
        seq += ["giu", "A"]                            # avviso "Basta cosi'"
        seq += ["A"] * SCHERMATE_FINALI
        con_tasti(i, seq)
        i.modalita_diceware()
    prova("dadi, annulla l'ultima parola con B) canc", dadi_annulla)

    def dadi_due_schermate():
        """Con piu' di 10 parole l'elenco numerato si spezza in due
        schermate (mostra_passphrase): qui si naviga davvero alla seconda
        pagina con la freccia invece di limitarsi a premere subito A,
        cosi' anche quel percorso viene ripercorso e non solo letto."""
        tiri = ["52431", "11111", "66666", "34251", "16234", "44444",
                "22222", "33333", "55555", "65432", "14263", "36251"]
        seq = ["A", "A"]
        for n, t in enumerate(tiri):
            seq += tasti_per_dadi(i, t)
            seq.append("Y" if n == len(tiri) - 1 else "A")
        seq += ["A", "A", "A"]        # i tre avvisi prima dell'elenco
        seq += ["destra", "A"]        # elenco su due pagine: vai alla seconda, poi fine
        seq += ["A", "A"]             # i due avvisi prima della passphrase intera
        seq += ["A"]                  # passphrase intera
        con_tasti(i, seq)
        i.modalita_diceware()
    prova("dadi, 12 parole, doppia schermata dell'elenco", dadi_due_schermate)

    print("\nMENU")

    def info():
        con_tasti(i, ["giu", "giu", "A", "A", "B"])
        try:
            i.avvia()
        except Exception as e:
            if "sequenza finita" not in str(e):
                raise
    prova("menu, voce Informazioni", info)

    print("\n" + "=" * 54)
    falliti = [(n, e) for n, e in _esiti if e]
    if falliti:
        print("  %d PERCORSI FALLITI su %d" % (len(falliti), len(_esiti)))
        print("=" * 54)
        for n, e in falliti:
            print("  %s\n     %r" % (n, e))
    else:
        print("  TUTTI I %d PERCORSI SUPERATI" % len(_esiti))
        print("=" * 54)
    gc.collect()
    print("\nRAM libera: %d KB" % (gc.mem_free() // 1024))


esegui()
