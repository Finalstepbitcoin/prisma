#!/usr/bin/env python3
"""
prepara_diceware.py  --  Final Step Bitcoin / Checksum Tool

Scarica le due liste Diceware pubblicate sul sito e le trasforma nei file
che il dispositivo puo' leggere.

QUESTO SCRIPT GIRA SOLO SUL MAC, quando serve. Non finisce nel dispositivo.

LE DUE LISTE SONO QUELLE DEL SITO, NON ALTRE:
  - inglese  : Arnold Reinhold, l'inventore del metodo.  Licenza CC-BY 4.0
  - italiana : Tarin Gamberini.                          Licenza GPL-3.0

Le liste NON vengono messe nel repository: si scaricano al momento, dalle
fonti originali. Cosi' il codice del progetto resta tutto nostro e la
licenza di ciascuna lista resta la sua.

REGOLA DA NON VIOLARE: le voci si copiano ESATTAMENTE come sono, comprese
quelle con simboli e apostrofi (a&p, i've) o le cifre nude (0, 12).
"Ripulirle" spezzerebbe la corrispondenza col numero uscito dai dadi, e il
dispositivo direbbe una cosa diversa dalla scheda di carta e da qualunque
altro strumento Diceware.

Uso:
    python3 prepara_diceware.py
"""

import hashlib
import re
import sys
import urllib.request

# "impronta_attesa": la SHA-256 della lista scaricata e verificata il 21
# agosto 2026, quella con cui e' stato costruito il dispositivo. Se la fonte
# restituisse un contenuto diverso lo script si ferma prima di generare
# firmware da una lista diversa da quella attesa.
#
# Per aggiornarla DI PROPOSITO: scarica la nuova lista, controllane il
# contenuto a mano (es. confrontandola con la scheda di carta pubblicata),
# poi incolla qui il nuovo SHA-256.
LISTE = [
    {
        "nome": "inglese",
        "file": "diceware_en.py",
        "autore": "Arnold Reinhold",
        "licenza": "CC-BY 4.0",
        "url": "https://theworld.com/~reinhold/diceware.wordlist.asc",
        "pagina": "https://theworld.com/~reinhold/diceware.html",
        "impronta_attesa": "3cd6164a99e95381f8620aec782a933545bcd5833fa331d267a6829f6665256e",
    },
    {
        "nome": "italiana",
        "file": "diceware_it.py",
        "autore": "Tarin Gamberini",
        "licenza": "GPL-3.0-or-later",
        "url": "https://www.taringamberini.com/downloads/diceware_it_IT/"
               "lista-di-parole-diceware-in-italiano/4/"
               "word_list_diceware_it-IT-4.txt",
        "pagina": "https://www.taringamberini.com/it/diceware_it_IT/"
                  "lista-di-parole-diceware-in-italiano/",
        "impronta_attesa": "b441559b64fb7041b9bbcecb3c43111f2523ec84e172670409f40c462eda0b93",
    },
]

LARGHEZZA = 6      # la voce piu' lunga, in entrambe le liste, e' di 6 caratteri
ATTESE = 7776      # 6^5: cinque dadi a sei facce


def scarica(url):
    print("  scarico: %s" % url)
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def estrai(testo):
    """Prende le coppie 'codice a 5 cifre' + 'voce'. Ignora tutto il resto."""
    return dict(re.findall(r"^([1-6]{5})[ \t]+(\S+)[ \t]*$", testo, re.M))


def controlla(voci):
    errori = []

    if len(voci) != ATTESE:
        errori.append("trovate %d voci invece di %d" % (len(voci), ATTESE))

    # devono esserci TUTTI i codici da 11111 a 66666, nessuno escluso
    mancanti = 0
    for n in range(ATTESE):
        codice = ""
        v = n
        for _ in range(5):
            codice = str(v % 6 + 1) + codice
            v //= 6
        if codice not in voci:
            mancanti += 1
    if mancanti:
        errori.append("mancano %d codici di dado" % mancanti)

    parole = list(voci.values())
    if len(set(parole)) != len(parole):
        errori.append("ci sono voci ripetute")

    troppo_lunghe = [p for p in parole if len(p) > LARGHEZZA]
    if troppo_lunghe:
        errori.append("voci piu' lunghe di %d caratteri: %r"
                      % (LARGHEZZA, troppo_lunghe[:5]))

    return errori


def indice(codice):
    """Dal codice dei dadi (es. '52431') alla posizione nella lista."""
    n = 0
    for c in codice:
        n = n * 6 + (int(c) - 1)
    return n


def genera(lista, voci, impronta):
    ordinate = [None] * ATTESE
    for codice, parola in voci.items():
        ordinate[indice(codice)] = parola

    blob = "".join(p.ljust(LARGHEZZA) for p in ordinate)

    righe = [
        '"""',
        "Lista Diceware %s - GENERATO AUTOMATICAMENTE, non modificare a mano." % lista["nome"],
        "",
        "Autore:   %s" % lista["autore"],
        "Licenza:  %s" % lista["licenza"],
        "Pagina:   %s" % lista["pagina"],
        "File:     %s" % lista["url"],
        "SHA-256:  %s" % impronta,
        "Voci:     %d   (cinque dadi a sei facce)" % ATTESE,
        "",
        "Per rigenerarlo:  python3 prepara_diceware.py",
        '"""',
        "",
        'NOME = "%s"' % lista["nome"],
        'AUTORE = "%s"' % lista["autore"],
        'LICENZA = "%s"' % lista["licenza"],
        'IMPRONTA = "%s"' % impronta,
        "N_VOCI = %d" % ATTESE,
        "LARGHEZZA = %d" % LARGHEZZA,
        "",
        "# le voci in ordine di codice: 11111 e' la prima, 66666 l'ultima",
        "BLOB = (",
    ]
    for i in range(0, ATTESE, 12):
        pezzo = "".join(p.ljust(LARGHEZZA) for p in ordinate[i:i + 12])
        righe.append('    "%s"' % pezzo.replace("\\", "\\\\").replace('"', '\\"'))
    righe.append(")")
    righe.append("")

    testo = "\n".join(righe)
    with open(lista["file"], "w", encoding="utf-8") as f:
        f.write(testo)

    # controprova: il file appena scritto si rilegge identico?
    ambiente = {}
    exec(compile(testo, lista["file"], "exec"), ambiente)
    b = ambiente["BLOB"]
    riletto = [b[i * LARGHEZZA:(i + 1) * LARGHEZZA].rstrip() for i in range(ATTESE)]
    if riletto != ordinate:
        print("ERRORE: il file generato non si rilegge correttamente.")
        sys.exit(1)

    return len(blob), ordinate


def main():
    print("=" * 62)
    print("  LISTE DICEWARE - le stesse pubblicate sul sito")
    print("=" * 62)

    for lista in LISTE:
        print("\nLista %s (%s, %s)" % (lista["nome"], lista["autore"], lista["licenza"]))
        testo = scarica(lista["url"])
        impronta = hashlib.sha256(testo.encode("utf-8")).hexdigest()

        if impronta != lista["impronta_attesa"]:
            print("  LISTA NON VALIDA, non genero niente:")
            print("    - impronta diversa da quella attesa")
            print("      atteso : %s" % lista["impronta_attesa"])
            print("      trovato: %s" % impronta)
            print("    Puo' essere una fonte cambiata (anche in modo legittimo)")
            print("    oppure qualcosa in mezzo al download. Controlla il nuovo")
            print("    contenuto a mano prima di aggiornare impronta_attesa qui.")
            sys.exit(1)

        voci = estrai(testo)

        errori = controlla(voci)
        if errori:
            print("  LISTA NON VALIDA, non genero niente:")
            for e in errori:
                print("    - %s" % e)
            sys.exit(1)

        print("  7776 voci, tutti i codici da 11111 a 66666 ... ok")
        print("  nessun doppione .............................. ok")
        print("  nessuna voce oltre %d caratteri ............... ok" % LARGHEZZA)

        byte, ordinate = genera(lista, voci, impronta)
        print("  generato %s  (%d byte)" % (lista["file"], byte))
        print("  SHA-256: %s" % impronta)
        print("  prova:   52431 -> %s" % ordinate[indice("52431")])

        strane = sum(1 for p in ordinate if not p.isalpha())
        print("  voci con simboli o cifre: %d (si copiano COSI' COME SONO)" % strane)

    print("\nFatto. Ora:  python3 test_diceware.py")


if __name__ == "__main__":
    main()
