#!/usr/bin/env python3
"""
prepara_impronta.py  --  Final Step Bitcoin / Checksum Tool

Calcola sul computer la stessa impronta che il dispositivo mostra
all'accensione.

GIRA SUL MAC. Serve per due cose:
  1. pubblicare sul sito e stampare sul foglietto le tre parole attese
  2. controllare che un dispositivo gia' montato mostri quelle giuste

Il calcolo e' identico a quello di impronta.py sul dispositivo:
  - mezzo megabyte di memoria flash dall'inizio (MicroPython, poi vuoto)
  - tutti i file .py installati, in ordine alfabetico, nome compreso

Uso:
    python3 prepara_impronta.py
"""

import hashlib
import os
import struct
import sys

import bip39_checksum as bip39

INIZIO_FLASH = 0x10000000
# ATTENZIONE, LIMITE SCELTO CON CURA (e' costato una caccia all'errore):
# a 0x7F000, cioe' a 508 KB dall'inizio, il Raspberry Pi scrive in fabbrica
# l'esito del proprio collaudo: data, ora e numero di serie della scheda.
# Sono DIVERSI SU OGNI ESEMPLARE. Se finissero nell'impronta, ogni
# dispositivo mostrerebbe tre parole diverse e nessun valore pubblicato
# potrebbe mai corrispondere. Ci fermiamo a 448 KB: sopra il firmware di
# MicroPython (circa 320 KB), sotto i dati di fabbrica.
ZONA_FIRMWARE = 448 * 1024
FAMIGLIA_RP2350 = 0xE48BFF59     # blocchi di programma per questo chip
PAROLE = 3

# La release di MicroPython con cui e' stato costruito il dispositivo,
# verificata il 21 agosto 2026. trova_uf2() non si fida piu' di "l'ultimo
# file .uf2 che trovo": il contenuto deve corrispondere esattamente a
# questo, altrimenti ci si potrebbe ritrovare a firmare come "impronta
# attesa" un'immagine sconosciuta o modificata.
#
# Per aggiornarla DI PROPOSITO (nuova versione di MicroPython): scarica il
# .uf2 da micropython.org, controllane la provenienza, poi incolla qui nome
# e SHA-256 del file nuovo.
UF2_ATTESO = {
    "nome": "RPI_PICO2-20260406-v1.28.0.uf2",
    "sha256": "e65ad62ae886a4f56da8ef2c07904fe504b92de69e5ae6489acf881bcf30b6ae",
}

# I file che vengono installati sul dispositivo. QUESTA LISTA E' LA STESSA
# usata da installa.py: se le due divergono, l'impronta calcolata qui non
# corrispondera' a quella mostrata dal dispositivo.
FILE_DISPOSITIVO = (
    "bip39_checksum.py",
    "diceware.py",
    "diceware_en.py",
    "diceware_it.py",
    "impronta.py",
    "interfaccia.py",
    "main.py",
    "qr_canale.py",
    "schermo.py",
    "wordlist.py",
)


def immagine_flash(percorso_uf2):
    """
    Ricostruisce come appare la memoria flash dopo aver caricato il .uf2.
    Le parti non scritte restano a 0xFF, come una memoria vuota.
    """
    memoria = bytearray(b"\xff" * ZONA_FIRMWARE)
    piu_lontano = [0]
    with open(percorso_uf2, "rb") as f:
        dati = f.read()
    if len(dati) % 512:
        print("ERRORE: %s non sembra un file .uf2 valido." % percorso_uf2)
        sys.exit(1)
    for i in range(len(dati) // 512):
        b = dati[i * 512:(i + 1) * 512]
        magico0, magico1, _, indirizzo, quanti = struct.unpack("<5I", b[:20])
        famiglia = struct.unpack("<I", b[28:32])[0]
        if magico0 != 0x0A324655 or magico1 != 0x9E5D5157:
            continue
        # Solo i blocchi di programma per l'RP2350. Il .uf2 ne contiene anche
        # uno speciale a 16 MB che serve da marcatore al bootloader: non e'
        # firmware e conteggiarlo faceva scattare un falso allarme.
        if famiglia != FAMIGLIA_RP2350:
            continue
        scarto = indirizzo - INIZIO_FLASH
        if 0 <= scarto < ZONA_FIRMWARE:
            fine = min(quanti, ZONA_FIRMWARE - scarto)
            memoria[scarto:scarto + fine] = b[32:32 + fine]
            piu_lontano[0] = max(piu_lontano[0], scarto + fine)
        elif 0 <= scarto < 16 * 1024 * 1024:
            piu_lontano[0] = max(piu_lontano[0], scarto + quanti)
    if piu_lontano[0] > ZONA_FIRMWARE:
        print("ATTENZIONE: il firmware arriva a %d KB, oltre i %d KB misurati."
              % (piu_lontano[0] // 1024, ZONA_FIRMWARE // 1024))
        print("L'impronta non lo coprirebbe tutto: va alzato ZONA_FIRMWARE")
        print("(ma restando sotto i 508 KB dei dati di fabbrica).")
        sys.exit(1)
    print("firmware: occupa %d KB dei %d misurati"
          % (piu_lontano[0] // 1024, ZONA_FIRMWARE // 1024))
    return bytes(memoria)


def trova_uf2():
    """
    Tutti i file .uf2 trovati in firmware/ o nella cartella corrente
    (non solo l'ultimo per nome: la scelta vera la fa verifica_uf2()
    confrontando il contenuto, non il nome del file).
    """
    trovati = []
    for cartella in ("firmware", "."):
        if not os.path.isdir(cartella):
            continue
        trovati += [os.path.join(cartella, f) for f in sorted(os.listdir(cartella))
                    if f.endswith(".uf2")]
    return trovati


def verifica_uf2(percorsi):
    """
    Fra i .uf2 trovati, quello il cui SHA-256 corrisponde a UF2_ATTESO.
    Rifiuta esplicitamente qualunque immagine sconosciuta o modificata:
    non basta che UN file .uf2 sia presente, deve essere PROPRIO quello.
    """
    if not percorsi:
        print("ERRORE: non trovo nessun file .uf2 di MicroPython.")
        print("Scaricalo da micropython.org e mettilo in firmware/")
        sys.exit(1)

    for percorso in percorsi:
        with open(percorso, "rb") as f:
            impronta = hashlib.sha256(f.read()).hexdigest()
        if impronta == UF2_ATTESO["sha256"]:
            return percorso

    print("ERRORE: nessuno dei file .uf2 trovati corrisponde alla release attesa.")
    print("  attesa: %s" % UF2_ATTESO["nome"])
    print("  SHA-256 atteso: %s" % UF2_ATTESO["sha256"])
    print("\nTrovati:")
    for percorso in percorsi:
        with open(percorso, "rb") as f:
            impronta = hashlib.sha256(f.read()).hexdigest()
        print("  %-50s SHA-256 %s" % (percorso, impronta))
    print("\nSe hai scaricato di proposito una versione nuova di MicroPython,")
    print("controllane la provenienza e poi aggiorna UF2_ATTESO in questo file.")
    sys.exit(1)


def parole_da(digest):
    valore = 0
    for b in digest[:5]:
        valore = (valore << 8) | b
    valore >>= (40 - 11 * PAROLE)
    return [bip39.parola((valore >> (11 * (PAROLE - 1 - i))) & 0x7FF)
            for i in range(PAROLE)]


def main():
    uf2 = verifica_uf2(trova_uf2())

    mancanti = [f for f in FILE_DISPOSITIVO if not os.path.exists(f)]
    if mancanti:
        print("ERRORE: mancano dei file da installare:")
        for f in mancanti:
            print("   %s" % f)
        print("\nLanciali prima: prepara_wordlist.py, prepara_diceware.py, prepara_qr.py")
        sys.exit(1)

    print("=" * 62)
    print("  IMPRONTA DEL FIRMWARE")
    print("=" * 62)
    print("\nMicroPython : %s" % uf2)

    h = hashlib.sha256()
    h.update(immagine_flash(uf2))
    for nome in sorted(FILE_DISPOSITIVO):
        h.update(nome.encode())
        with open(nome, "rb") as f:
            h.update(f.read())
        print("  %-20s %7d byte" % (nome, os.path.getsize(nome)))

    digest = h.digest()
    tre = parole_da(digest)

    print("\nSHA-256 completo:")
    print("  %s" % digest.hex())
    print("\nLE TRE PAROLE DA PUBBLICARE E STAMPARE:")
    print()
    print("      %s" % "  ".join(w.upper() for w in tre))
    print()
    print("Il dispositivo deve mostrare esattamente queste, all'accensione.")
    print("Se ne mostra altre, il contenuto e' diverso da questo.")


if __name__ == "__main__":
    main()
