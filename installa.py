#!/usr/bin/env python3
"""
installa.py  --  Final Step Bitcoin / Checksum Tool

Copia sul dispositivo tutti i file che gli servono, in un colpo solo.

GIRA SUL MAC, dopo aver caricato MicroPython sul Pico.

Uso:
    python3 installa.py
"""

import subprocess
import sys

# I file che vanno sul dispositivo. QUESTA LISTA E' LA STESSA usata da
# prepara_impronta.py: se le due divergono, l'impronta calcolata sul
# computer non corrispondera' a quella mostrata dal dispositivo.
FILE_DISPOSITIVO = (
    "wordlist.py",
    "bip39_checksum.py",
    "diceware.py",
    "diceware_en.py",
    "diceware_it.py",
    "qr_canale.py",
    "impronta.py",
    "schermo.py",
    "interfaccia.py",
    "main.py",
)


def main():
    print("Installo %d file sul dispositivo.\n" % len(FILE_DISPOSITIVO))
    for nome in FILE_DISPOSITIVO:
        esito = subprocess.run([sys.executable, "parla_col_pico.py", "copia", nome],
                               capture_output=True, text=True)
        if esito.returncode != 0:
            print("ERRORE copiando %s:" % nome)
            print(esito.stdout, esito.stderr)
            print("\nL'installazione si e' fermata qui. Ogni file copiato finora")
            print("e' stato sostituito solo dopo essere stato verificato byte per")
            print("byte, quindi nessuno di quelli e' a meta' o corrotto - ma i file")
            print("successivi a questo nell'elenco sono rimasti alla versione")
            print("precedente. Risolvi il problema e rilancia python3 installa.py:")
            print("ripetere e' innocuo, ricopia solo quello che manca o e' diverso.")
            return 1
        ultima = [r for r in esito.stdout.splitlines() if "Copiato" in r]
        print("  %-20s %s" % (nome, ultima[0] if ultima else "ok"))

    print("\nVerifica finale: ogni file installato corrisponde davvero a")
    print("quello sul computer? (prova contenuto per contenuto, non solo che")
    print("qualcosa con quel nome esista)")
    problemi = 0
    for nome in FILE_DISPOSITIVO:
        esito = subprocess.run([sys.executable, "parla_col_pico.py", "verifica", nome],
                               capture_output=True, text=True)
        riga = esito.stdout.strip().splitlines()
        print("  %s" % (riga[-1] if riga else "%s: errore sconosciuto" % nome))
        if esito.returncode != 0:
            problemi += 1
    if problemi:
        print("\n%d file NON corrispondono al manifest atteso. Rilancia" % problemi)
        print("python3 installa.py per completare, non e' un'operazione distruttiva.")
        return 1

    print("\nControllo che non siano rimasti file .py non previsti (residui di")
    print("un'installazione precedente, che cambierebbero l'impronta)...")
    presenti = elenco_dispositivo()
    if presenti is None:
        return 1
    attesi = set(FILE_DISPOSITIVO)
    estranei = sorted(n for n in presenti if n.endswith(".py") and n not in attesi)
    if estranei:
        print("\nATTENZIONE: sul dispositivo ci sono file .py non previsti:")
        for n in estranei:
            print("  - %s" % n)
        print("Rimuovili a mano prima di calcolare l'impronta finale.")
    else:
        print("  nessun file estraneo.")

    print("\nFatto: %d file installati e verificati. Stacca e riattacca il cavo,"
          % len(FILE_DISPOSITIVO))
    print("deve partire da solo.")
    return 0


def elenco_dispositivo():
    """Tutti i nomi presenti sul dispositivo, ripulendo l'output del comando."""
    esito = subprocess.run([sys.executable, "parla_col_pico.py", "elenco"],
                           capture_output=True, text=True)
    if esito.returncode != 0:
        print("ERRORE leggendo l'elenco dal dispositivo:")
        print(esito.stdout, esito.stderr)
        return None
    return [r.strip() for r in esito.stdout.splitlines() if r.strip()]


if __name__ == "__main__":
    sys.exit(main())
