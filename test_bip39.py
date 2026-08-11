#!/usr/bin/env python3
"""
test_bip39.py  --  Final Step Bitcoin / Checksum Tool

Verifica che il motore di calcolo sia corretto, confrontandolo con i
VETTORI DI TEST UFFICIALI dello standard BIP39.

I vettori sono l'elenco di casi noti pubblicato insieme allo standard:
"con questa entropia deve uscire esattamente questa frase". Se il nostro
codice li supera tutti, la matematica e' dimostrata giusta - non sperata.

GIRA SUL MAC. Serve internet solo per scaricare i vettori.

Uso:
    python3 prepara_wordlist.py    (una volta sola, prima)
    python3 test_bip39.py
"""

import json
import sys
import urllib.request

try:
    import bip39_checksum as bip39
except ImportError:
    print("ERRORE: manca wordlist.py.")
    print("Lancia prima:  python3 prepara_wordlist.py")
    sys.exit(1)


FONTI_VETTORI = [
    "https://raw.githubusercontent.com/trezor/python-mnemonic/master/vectors.json",
    "https://raw.githubusercontent.com/trezor/python-mnemonic/master/tests/vectors.json",
]

# Quante ultime parole valide devono esistere, per ogni lunghezza di frase.
# L'ultima parola vale 11 bit, di cui (n/3) sono checksum obbligato:
# restano 11-(n/3) bit liberi, quindi 2^(11-n/3) possibilita'.
ATTESE = {12: 128, 15: 64, 18: 32, 21: 16, 24: 8}

_falliti = []
_passati = [0]


def verifica(condizione, descrizione):
    if condizione:
        _passati[0] += 1
    else:
        _falliti.append(descrizione)


def titolo(t):
    print("\n" + t)
    print("-" * len(t))


# ---------------------------------------------------------------------------

def scarica_vettori():
    for url in FONTI_VETTORI:
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                dati = json.loads(r.read().decode("utf-8"))
            voci = dati.get("english", [])
            if voci:
                print("Vettori ufficiali scaricati da:\n  %s" % url)
                return voci
        except Exception:
            continue
    print("ERRORE: non riesco a scaricare i vettori ufficiali BIP39.")
    print("Sei collegato a internet?")
    sys.exit(1)


# ---------------------------------------------------------------------------

def test_dizionario():
    titolo("1. Il dizionario")

    verifica(bip39.N_PAROLE == 2048, "il dizionario non ha 2048 parole")
    verifica(bip39.parola(0) == "abandon", "la prima parola non e' 'abandon'")
    verifica(bip39.parola(2047) == "zoo", "l'ultima parola non e' 'zoo'")

    # ogni parola si ritrova al suo posto
    ok = all(bip39.indice_di(bip39.parola(i)) == i for i in range(bip39.N_PAROLE))
    verifica(ok, "una parola non si ritrova al proprio indice")

    # parole inventate: non devono essere trovate
    verifica(bip39.indice_di("bitcoin") is None, "'bitcoin' non e' nel BIP39 ma viene trovata")
    verifica(bip39.indice_di("zzzz") is None, "'zzzz' viene trovata")

    print("  2048 parole, ricerca e indici .............. %s"
          % ("ok" if not _falliti else "ERRORE"))


def test_autocompletamento():
    titolo("2. Autocompletamento")

    verifica(bip39.completa("aban") == ["abandon"],
             "completa('aban') non da' solo 'abandon'")
    verifica(bip39.parola_unica("aban") == "abandon",
             "parola_unica('aban') non funziona")
    verifica(bip39.parola_unica("ab") is None,
             "parola_unica('ab') dovrebbe essere ambigua")
    # dopo "abo" esistono ancora due strade: about, above
    verifica(bip39.lettere_possibili("abo") == ["u", "v"],
             "dopo 'abo' dovrebbero restare 'u' e 'v'")
    verifica(bip39.lettere_possibili("abou") == ["t"],
             "dopo 'abou' dovrebbe restare solo la 't'")
    verifica(bip39.lettere_possibili("zoo") == [],
             "dopo 'zoo' non deve restare nessuna lettera")

    # la regola che rende veloce l'inserimento:
    # 4 lettere bastano SEMPRE a identificare una parola
    quattro = [bip39.parola(i)[:4] for i in range(bip39.N_PAROLE)]
    verifica(len(set(quattro)) == 2048,
             "le prime 4 lettere non sono univoche")

    # nessuna parola richiede piu' di 4 caratteri per essere identificata
    peggiore = max(
        (len(bip39.parola(i)) if len(bip39.completa(bip39.parola(i)[:4])) > 1 else 4)
        for i in range(0, bip39.N_PAROLE, 1)
    )
    verifica(peggiore <= 4, "serve piu' di 4 lettere per qualche parola")

    n_lettere = len(bip39.lettere_possibili(""))
    print("  4 lettere identificano sempre la parola .... ok")
    print("  lettere iniziali possibili ................. %d su 26" % n_lettere)


def test_vettori(voci):
    titolo("3. Vettori ufficiali BIP39 (%d casi)" % len(voci))

    per_lunghezza = {}
    for voce in voci:
        entropia_hex, frase = voce[0], voce[1]
        parole = frase.split()
        per_lunghezza[len(parole)] = per_lunghezza.get(len(parole), 0) + 1

        verifica(bip39.frase_valida(parole),
                 "frase ufficiale giudicata NON valida: %s..." % frase[:40])

        verifica(bip39.entropia_di(parole).hex() == entropia_hex.lower(),
                 "entropia diversa da quella attesa: %s..." % frase[:40])

    for n in sorted(per_lunghezza):
        print("  frasi da %2d parole: %2d casi ................ ok"
              % (n, per_lunghezza[n]))


def test_ultime_parole(voci):
    titolo("4. Calcolo delle ultime parole valide")

    controllate = {}
    for voce in voci:
        parole = voce[1].split()
        n = len(parole)
        if n not in ATTESE:
            continue

        parziale = parole[:-1]
        vera = parole[-1]
        valide = bip39.ultime_parole_valide(parziale)

        verifica(vera in valide,
                 "la parola vera '%s' non compare tra le valide" % vera)
        verifica(len(valide) == ATTESE[n],
                 "per %d parole ne ho trovate %d invece di %d"
                 % (n, len(valide), ATTESE[n]))
        verifica(len(set(valide)) == len(valide),
                 "ci sono doppioni tra le parole valide")

        # controprova: tutte le altre parole devono dare frase NON valida
        if n not in controllate:
            insieme = set(valide)
            sbagliate = 0
            for i in range(bip39.N_PAROLE):
                p = bip39.parola(i)
                if p in insieme:
                    continue
                if bip39.frase_valida(parziale + [p]):
                    sbagliate += 1
            verifica(sbagliate == 0,
                     "%d parole fuori elenco risultano valide" % sbagliate)

        controllate[n] = controllate.get(n, 0) + 1

    for n in sorted(controllate):
        print("  %2d parole -> %3d ultime parole valide ...... ok  (%d casi)"
              % (n - 1, ATTESE[n], controllate[n]))


def test_versione_veloce(voci):
    titolo("5. La versione veloce concorda con quella di riferimento")

    # La versione che gira sul dispositivo e' ottimizzata. Qui controlliamo
    # che dia ESATTAMENTE gli stessi risultati di quella lenta e ovvia.
    confronti = 0
    for voce in voci:
        parole = voce[1].split()
        parziale = parole[:-1]
        veloce = bip39.ultime_parole_valide(parziale)
        lenta = bip39.ultime_parole_valide_riferimento(parziale)
        verifica(veloce == lenta,
                 "le due versioni danno risultati diversi per: %s..." % voce[1][:40])
        confronti += 1

    # anche su frasi inventate, non solo sui vettori ufficiali
    for base in (["abandon"] * 11, ["zoo"] * 11, ["zoo"] * 23,
                 ["legal", "winner", "thank", "year", "wave", "sausage",
                  "worth", "useful", "legal", "winner", "thank"]):
        verifica(bip39.ultime_parole_valide(base) ==
                 bip39.ultime_parole_valide_riferimento(base),
                 "le due versioni divergono su %s..." % " ".join(base[:3]))
        confronti += 1

    print("  %d confronti, risultati identici ............ ok" % confronti)


def test_bit_liberi(voci):
    titolo("6. I bit dei lanci di moneta finiscono al posto giusto")

    # L'ultima parola contiene bit di entropia LIBERI (7 su 12 parole,
    # 3 su 24). Il dispositivo li fa fornire con lanci di moneta e poi usa
    # quel numero come posizione nell'elenco delle candidate.
    # Qui verifichiamo che sia davvero cosi': se fosse sbagliato, il
    # dispositivo darebbe una parola valida ma DIVERSA da quella che
    # l'entropia dell'utente indica, e nessuno se ne accorgerebbe.
    BIT = {12: 7, 24: 3}
    provati = {}
    for voce in voci:
        parole = voce[1].split()
        n = len(parole)
        if n not in BIT:
            continue
        parziale = parole[:-1]
        valide = bip39.ultime_parole_valide(parziale)
        liberi = BIT[n]

        for atteso in range(len(valide)):
            completa = parziale + [valide[atteso]]
            entropia = bip39.entropia_di(completa)
            valore = int.from_bytes(entropia, "big")
            letto = valore & ((1 << liberi) - 1)
            if letto != atteso:
                verifica(False, "posizione %d nell'elenco -> bit %d (per %d parole)"
                         % (atteso, letto, n))
                break
        else:
            verifica(True, "")
        provati[n] = provati.get(n, 0) + 1

    for n in sorted(provati):
        print("  frasi da %d parole: %d bit liberi ....... ok  (%d casi)"
              % (n, BIT[n], provati[n]))


def test_rifiuti():
    titolo("7. Casi che devono essere RIFIUTATI")

    verifica(not bip39.frase_valida("abandon abandon abandon"),
             "una frase da 3 parole viene accettata")
    verifica(not bip39.frase_valida(
        "abandon abandon abandon abandon abandon abandon "
        "abandon abandon abandon abandon abandon abandon"),
        "una frase con checksum sbagliato viene accettata")
    verifica(not bip39.frase_valida(
        "bitcoin abandon abandon abandon abandon abandon "
        "abandon abandon abandon abandon abandon about"),
        "una frase con parola inesistente viene accettata")

    try:
        bip39.ultime_parole_valide(["abandon"] * 5)
        verifica(False, "accetta un numero di parole non valido")
    except ValueError:
        verifica(True, "")

    try:
        bip39.ultime_parole_valide(["bitcoin"] * 11)
        verifica(False, "accetta una parola fuori dizionario")
    except ValueError:
        verifica(True, "")

    print("  frasi corte, checksum errati, parole finte .. tutte rifiutate")


def esempio_pratico():
    titolo("8. Esempio pratico")

    undici = ("legal winner thank year wave sausage worth useful "
              "legal winner thank")
    valide = bip39.ultime_parole_valide(undici)
    print("  Inserite 11 parole (le prime della frase di test ufficiale).")
    print("  Ultime parole valide trovate: %d" % len(valide))
    print("  Le prime dieci: %s" % ", ".join(valide[:10]))
    print("  ...")
    print("  Le ultime tre:  %s" % ", ".join(valide[-3:]))
    print("\n  L'utente ne sceglie una: sono tutte corrette.")


# ---------------------------------------------------------------------------

def main():
    print("=" * 62)
    print("  VERIFICA DEL MOTORE BIP39 - Final Step Bitcoin")
    print("=" * 62)
    print()

    voci = scarica_vettori()

    test_dizionario()
    test_autocompletamento()
    test_vettori(voci)
    test_ultime_parole(voci)
    test_versione_veloce(voci)
    test_bit_liberi(voci)
    test_rifiuti()
    esempio_pratico()

    print()
    print("=" * 62)
    if _falliti:
        print("  %d CONTROLLI FALLITI su %d" % (len(_falliti), len(_falliti) + _passati[0]))
        print("=" * 62)
        for f in _falliti[:20]:
            print("  - %s" % f)
        sys.exit(1)
    else:
        print("  TUTTI I %d CONTROLLI SUPERATI" % _passati[0])
        print("=" * 62)
        print()
        print("  Il calcolo del checksum e' conforme allo standard BIP39.")
        print("  Lo stesso codice girera' identico sul dispositivo.")


if __name__ == "__main__":
    main()
