#!/usr/bin/env python3
"""
prepara_wordlist.py  --  Final Step Bitcoin / Sintesi

Scarica il dizionario ufficiale BIP39 (inglese, 2048 parole) e genera il
file  wordlist.py  che verra' incluso nel firmware.

QUESTO SCRIPT GIRA SOLO SUL MAC, UNA VOLTA SOLA.
Non finisce dentro il dispositivo. E' l'unico pezzo che usa internet.

Uso:
    python3 prepara_wordlist.py

Perche' non ho scritto le 2048 parole a mano: un solo errore di battitura
renderebbe il dispositivo sbagliato in modo silenzioso. Meglio prenderle
dalla fonte ufficiale e controllarle automaticamente.
"""

import hashlib
import sys
import urllib.request

# Fonti ufficiali, in ordine di preferenza.
# La prima e' il repository dei BIP stessi: piu' canonica di cosi' non si puo'.
FONTI = [
    "https://raw.githubusercontent.com/bitcoin/bips/master/bip-0039/english.txt",
    "https://raw.githubusercontent.com/trezor/python-mnemonic/master/src/mnemonic/wordlist/english.txt",
]

LARGHEZZA = 8   # la parola BIP39 piu' lunga e' di 8 lettere

# Impronta del dizionario scaricato e verificato il 21 agosto 2026, quello
# con cui e' stato costruito il dispositivo. Se una fonte restituisse un
# contenuto diverso - fonte cambiata, o qualcosa in mezzo al download - lo
# script si ferma qui sotto invece di generare firmware da un dizionario
# diverso da quello atteso.
#
# Per aggiornarla DI PROPOSITO (es. viene corretto un refuso nel repository
# BIP ufficiale): scarica il nuovo dizionario, controllane il contenuto a
# mano confrontandolo con un'altra fonte indipendente, poi incolla qui il
# nuovo SHA-256.
IMPRONTA_ATTESA = "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"


def scarica():
    """
    Interroga TUTTE le fonti raggiungibili, non si ferma alla prima che
    risponde: se sono d'accordo fra loro e' un controllo in piu' (una fonte
    compromessa o un mirror indietro di un aggiornamento verrebbe scoperto
    dal confronto), se non lo sono lo script si ferma invece di scegliere
    a caso quale credere.
    """
    risultati = []
    for url in FONTI:
        try:
            print("Scarico da: %s" % url)
            with urllib.request.urlopen(url, timeout=30) as r:
                testo = r.read().decode("utf-8")
            risultati.append((url, testo))
        except Exception as e:
            print("   non riuscito (%s)" % e)

    if not risultati:
        print("\nERRORE: nessuna fonte raggiungibile. Sei collegato a internet?")
        sys.exit(1)

    if len(risultati) > 1:
        impronte = {hashlib.sha256(t.encode("utf-8")).hexdigest() for _, t in risultati}
        if len(impronte) > 1:
            print("\nERRORE: le fonti raggiunte NON sono d'accordo fra loro:")
            for url, t in risultati:
                print("  %s" % url)
                print("    SHA-256: %s" % hashlib.sha256(t.encode("utf-8")).hexdigest())
            print("Non genero niente finche' non e' chiaro quale sia quella giusta.")
            sys.exit(1)
        print("Le %d fonti raggiunte sono d'accordo fra loro." % len(risultati))

    url_prima, testo_primo = risultati[0]
    return testo_primo, url_prima


def controlla(parole):
    """Controlli strutturali. Se uno solo fallisce, non generiamo niente."""
    errori = []

    if len(parole) != 2048:
        errori.append("il dizionario ha %d parole invece di 2048" % len(parole))

    for p in parole:
        if not p.isascii() or not p.isalpha() or not p.islower():
            errori.append("parola non valida: %r" % p)
            break

    if any(len(p) > LARGHEZZA for p in parole):
        lunga = max(parole, key=len)
        errori.append("parola piu' lunga di %d lettere: %r" % (LARGHEZZA, lunga))

    if parole != sorted(parole):
        errori.append("il dizionario non e' in ordine alfabetico")

    if len(set(parole)) != len(parole):
        errori.append("ci sono parole ripetute")

    # Regola BIP39: le prime 4 lettere identificano la parola in modo univoco.
    # E' cio' che rende possibile l'autocompletamento veloce.
    prefissi = set(p[:4] for p in parole)
    if len(prefissi) != len(parole):
        errori.append("le prime 4 lettere non sono univoche")

    return errori


def genera(parole, impronta, url):
    """
    Scrive wordlist.py come un'unica stringa a larghezza fissa.

    Perche' una stringa unica e non una lista di 2048 parole: sul dispositivo
    una lista occuperebbe circa 100 KB di RAM. Cosi' invece il dizionario resta
    nella memoria flash e le parole vengono estratte solo quando servono.
    """
    blob = "".join(p.ljust(LARGHEZZA) for p in parole)

    righe = []
    righe.append('"""')
    righe.append("Dizionario BIP39 inglese - GENERATO AUTOMATICAMENTE, non modificare a mano.")
    righe.append("")
    righe.append("Fonte:    %s" % url)
    righe.append("SHA-256:  %s" % impronta)
    righe.append("Parole:   %d" % len(parole))
    righe.append("")
    righe.append("Per rigenerarlo:  python3 prepara_wordlist.py")
    righe.append('"""')
    righe.append("")
    righe.append("N_PAROLE = %d" % len(parole))
    righe.append("LARGHEZZA = %d" % LARGHEZZA)
    righe.append('IMPRONTA_DIZIONARIO = "%s"' % impronta)
    righe.append("")
    righe.append("# 2048 parole, ognuna riempita di spazi fino a %d caratteri." % LARGHEZZA)
    righe.append("BLOB = (")
    # spezzo in righe da 8 parole per non avere una riga da 16 KB
    for i in range(0, len(parole), 8):
        pezzo = "".join(p.ljust(LARGHEZZA) for p in parole[i:i + 8])
        righe.append('    "%s"' % pezzo)
    righe.append(")")
    righe.append("")

    testo = "\n".join(righe)

    with open("wordlist.py", "w", encoding="utf-8") as f:
        f.write(testo)

    # controllo finale: quello che ho scritto si rilegge identico?
    ambiente = {}
    exec(compile(testo, "wordlist.py", "exec"), ambiente)
    riletto = [ambiente["BLOB"][i * LARGHEZZA:(i + 1) * LARGHEZZA].rstrip()
               for i in range(len(parole))]
    if riletto != parole:
        print("ERRORE: il file generato non si rilegge correttamente.")
        sys.exit(1)

    return len(blob)


def main():
    testo, url = scarica()
    impronta = hashlib.sha256(testo.encode("utf-8")).hexdigest()
    parole = testo.split()

    if impronta != IMPRONTA_ATTESA:
        print("\nERRORE: il dizionario scaricato NON corrisponde al valore atteso.")
        print("  atteso : %s" % IMPRONTA_ATTESA)
        print("  trovato: %s" % impronta)
        print("\nPuo' essere una fonte cambiata (anche in modo legittimo) oppure")
        print("qualcosa che si e' messo in mezzo al download. Non genero niente")
        print("finche' non e' chiaro quale dei due casi sia: controlla il nuovo")
        print("contenuto a mano prima di aggiornare IMPRONTA_ATTESA in questo file.")
        sys.exit(1)

    print("\nControllo il dizionario...")
    errori = controlla(parole)
    if errori:
        print("\nDIZIONARIO NON VALIDO, non genero niente:")
        for e in errori:
            print("  - %s" % e)
        sys.exit(1)

    print("  2048 parole ............................. ok")
    print("  tutte minuscole, solo lettere ........... ok")
    print("  ordine alfabetico ....................... ok")
    print("  nessun doppione ......................... ok")
    print("  prime 4 lettere univoche ................ ok")

    byte = genera(parole, impronta, url)

    print("\nGenerato: wordlist.py  (%d byte di dizionario)" % byte)
    print("SHA-256 del file scaricato:")
    print("  %s" % impronta)
    print("\nPrima parola: %s     Ultima parola: %s" % (parole[0], parole[-1]))
    print("\nOra puoi lanciare:  python3 test_bip39.py")


if __name__ == "__main__":
    main()
