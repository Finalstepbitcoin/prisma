#!/usr/bin/env python3
"""
test_diceware.py  --  Final Step Bitcoin / Checksum Tool

Verifica che la traduzione dai dadi alle parole sia corretta, confrontandola
con le liste ufficiali riscaricate dalle fonti.

GIRA SUL MAC. Serve internet.

Uso:
    python3 prepara_diceware.py     (una volta, prima)
    python3 test_diceware.py
"""

import hashlib
import re
import sys
import urllib.request

import diceware
from prepara_diceware import ATTESE, LISTE, indice

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


def test_bit():
    titolo("1. Il contatore dell'entropia")

    # Devono uscire gli STESSI numeri stampati sulla scheda di carta.
    carta = ["12,9", "25,8", "38,8", "51,7", "64,6",
             "77,5", "90,5", "103,4", "116,3", "129,2"]
    for n, atteso in enumerate(carta, start=1):
        letto = diceware.bit_testo(n)
        verifica(letto == atteso,
                 "con %d parole lo schermo direbbe %s ma la carta dice %s"
                 % (n, letto, atteso))
    print("  i dieci valori coincidono con la scheda .... ok")
    print("  %s" % "  ".join(carta[:5]))
    print("  %s" % "  ".join(carta[5:]))


def test_lista(codice, dati):
    titolo("Lista %s (%s)" % (dati["nome"], dati["licenza"]))

    L = diceware.Lista(codice)

    # riscarico la lista dalla fonte e confronto voce per voce
    with urllib.request.urlopen(dati["url"], timeout=60) as r:
        testo = r.read().decode("utf-8", "replace")

    # non basta che la fonte risponda: deve essere la STESSA fonte gia'
    # pinnata in prepara_diceware.py, altrimenti questo test si limiterebbe
    # a fidarsi di un secondo download della stessa fonte, magari compromessa
    # allo stesso modo del primo.
    impronta = hashlib.sha256(testo.encode("utf-8")).hexdigest()
    verifica(impronta == dati["impronta_attesa"],
             "la fonte %s non corrisponde piu' all'impronta pinnata "
             "(atteso %s, trovato %s)"
             % (dati["nome"], dati["impronta_attesa"], impronta))
    if impronta != dati["impronta_attesa"]:
        # la fonte e' cambiata: confrontare voce per voce col dispositivo
        # non direbbe niente di utile in piu', solo altri errori a catena
        # con la stessa causa. Meglio fermarsi qui ed essere chiari.
        print("  fonte diversa dal valore pinnato: salto i controlli restanti")
        return

    vere = dict(re.findall(r"^([1-6]{5})[ \t]+(\S+)[ \t]*$", testo, re.M))
    verifica(len(vere) == ATTESE, "la fonte non ha %d voci" % ATTESE)

    diverse = 0
    for codice_dadi, parola in vere.items():
        if L.parola(codice_dadi) != parola:
            diverse += 1
    verifica(diverse == 0,
             "%d voci diverse fra il dispositivo e la fonte" % diverse)
    print("  tutte le %d voci coincidono con la fonte ... ok" % ATTESE)

    # gli estremi e l'esempio della scheda di carta
    verifica(L.indice("11111") == 0, "11111 non e' la prima voce")
    verifica(L.indice("66666") == ATTESE - 1, "66666 non e' l'ultima voce")
    print("  11111 -> %-8s      66666 -> %s"
          % (L.parola("11111"), L.parola("66666")))
    print("  52431 -> %s   (l'esempio stampato sulla scheda)"
          % L.parola("52431"))

    # ogni codice dei dadi da' una voce, e tutte le posizioni sono coperte
    viste = set()
    for n in range(ATTESE):
        c = ""
        v = n
        for _ in range(5):
            c = str(v % 6 + 1) + c
            v //= 6
        viste.add(L.indice(c))
    verifica(len(viste) == ATTESE,
             "i 7776 tiri non coprono tutte le posizioni")
    print("  i 7776 tiri coprono tutte le voci ......... ok")

    # tiri impossibili: devono essere rifiutati
    for cattivo in ("11", "1111111", "11117", "11110", "abcde"):
        try:
            L.parola(cattivo)
            verifica(False, "accettato un tiro impossibile: %s" % cattivo)
        except (ValueError, TypeError):
            verifica(True, "")
    print("  tiri impossibili rifiutati ................ ok")

    strane = [L.parola("%d%d%d%d%d" % tuple((n // 6 ** k) % 6 + 1 for k in range(4, -1, -1)))
              for n in range(ATTESE)]
    n_strane = sum(1 for p in strane if L.voce_strana(p))
    print("  voci con simboli o cifre: %d (mostrate come sono)" % n_strane)


def main():
    print("=" * 62)
    print("  VERIFICA DELLE LISTE DICEWARE")
    print("=" * 62)

    test_bit()
    for codice, dati in zip(("en", "it"), LISTE):
        test_lista(codice, dati)

    print()
    print("=" * 62)
    if _falliti:
        print("  %d CONTROLLI FALLITI su %d"
              % (len(_falliti), len(_falliti) + _passati[0]))
        print("=" * 62)
        for f in _falliti[:20]:
            print("  - %s" % f)
        sys.exit(1)
    print("  TUTTI I %d CONTROLLI SUPERATI" % _passati[0])
    print("=" * 62)
    print()
    print("  Le liste sul dispositivo sono identiche a quelle pubblicate,")
    print("  e il contatore dei bit dice le stesse cose della scheda.")


if __name__ == "__main__":
    main()
