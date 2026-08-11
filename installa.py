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
            return 1
        ultima = [r for r in esito.stdout.splitlines() if "Copiato" in r]
        print("  %-20s %s" % (nome, ultima[0] if ultima else "ok"))
    print("\nFatto. Stacca e riattacca: deve partire da solo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
