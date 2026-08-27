#!/usr/bin/env python3
"""
prova_uf2.py  --  Final Step Bitcoin / Prisma

Controlla il file unico prodotto da crea_uf2.py, senza bisogno del
dispositivo: lo rilegge e ricostruisce com'e' fatta la memoria del Pico
dopo averlo caricato, poi verifica che dentro ci sia esattamente quello
che deve esserci.

Uso:
    .venv-strumenti/bin/python prova_uf2.py
"""

import hashlib
import struct
import sys

import crea_uf2 as c
import prepara_impronta as imp

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


def leggi_blocchi(percorso):
    """Ogni blocco, con dentro tutti i suoi campi."""
    with open(percorso, "rb") as f:
        dati = f.read()
    fuori = []
    for i in range(len(dati) // 512):
        b = dati[i * 512:(i + 1) * 512]
        m0, m1, bandiere, indirizzo, quanti, numero, totale, famiglia = \
            struct.unpack("<8I", b[:32])
        fine = struct.unpack("<I", b[508:512])[0]
        fuori.append(dict(m0=m0, m1=m1, bandiere=bandiere, indirizzo=indirizzo,
                          quanti=quanti, numero=numero, totale=totale,
                          famiglia=famiglia, fine=fine, dati=b[32:32 + quanti]))
    return fuori


def memoria_da(blocchi, inizio, quanti_byte):
    """Come appare un tratto di memoria dopo aver caricato questi blocchi."""
    memoria = bytearray(b"\xff" * quanti_byte)
    for b in blocchi:
        scarto = b["indirizzo"] - inizio
        if 0 <= scarto < quanti_byte:
            memoria[scarto:scarto + len(b["dati"])] = b["dati"]
    return bytes(memoria)


def main():
    uscita = "prisma-%s.uf2" % c.VERSIONE
    ufficiale = imp.verifica_uf2(imp.trova_uf2())

    print("=" * 62)
    print("  VERIFICA DEL FILE UNICO")
    print("=" * 62)
    print("\nfile da controllare : %s" % uscita)
    print("MicroPython di       : %s" % ufficiale)

    try:
        blocchi = leggi_blocchi(uscita)
    except FileNotFoundError:
        print("\nERRORE: manca %s. Lancia prima crea_uf2.py" % uscita)
        sys.exit(1)

    # ------------------------------------------------------------------
    titolo("1. Il formato del file")

    verifica(all(b["m0"] == c.UF2_MAGIC0 and b["m1"] == c.UF2_MAGIC1
                 for b in blocchi), "un blocco non ha la firma .uf2 giusta")
    verifica(all(b["fine"] == c.UF2_MAGIC_FINE for b in blocchi),
             "un blocco non ha la firma finale giusta")
    verifica(all(b["quanti"] <= 256 for b in blocchi),
             "un blocco dichiara piu' di 256 byte utili")

    # LA NUMERAZIONE: e' il punto in cui accodare due file rompe tutto.
    verifica([b["numero"] for b in blocchi] == list(range(len(blocchi))),
             "i blocchi non sono numerati di fila da 0")
    verifica(all(b["totale"] == len(blocchi) for b in blocchi),
             "non tutti i blocchi dichiarano lo stesso totale")
    print("  %d blocchi, firme e numerazione ............ ok" % len(blocchi))

    # ------------------------------------------------------------------
    titolo("2. MicroPython non e' stato toccato")

    nostri = memoria_da(blocchi, c.INIZIO_FLASH, imp.ZONA_FIRMWARE)
    loro = memoria_da(leggi_blocchi(ufficiale), c.INIZIO_FLASH, imp.ZONA_FIRMWARE)
    verifica(nostri == loro,
             "la zona del firmware non coincide con quella del .uf2 ufficiale")
    print("  i primi %d KB sono identici al .uf2 ufficiale  ok"
          % (imp.ZONA_FIRMWARE // 1024))

    # ------------------------------------------------------------------
    titolo("3. I due gruppi non si pestano i piedi")

    fine_firmware = max(b["indirizzo"] + len(b["dati"]) for b in blocchi
                        if b["indirizzo"] < c.INIZIO_FLASH + c.ARCHIVIO_INIZIO
                        and b["indirizzo"] >= c.INIZIO_FLASH
                        and b["famiglia"] == imp.FAMIGLIA_RP2350)
    inizio_archivio = c.INIZIO_FLASH + c.ARCHIVIO_INIZIO
    verifica(fine_firmware <= inizio_archivio,
             "il firmware arriva dentro la zona dell'archivio")
    print("  il firmware finisce a  %d KB" % ((fine_firmware - c.INIZIO_FLASH)//1024))
    print("  l'archivio comincia a  %d KB" % (c.ARCHIVIO_INIZIO // 1024))

    # i dati di collaudo di fabbrica (508 KB) devono restare intoccati
    collaudo = c.INIZIO_FLASH + 0x7F000
    tocca = [b for b in blocchi
             if b["indirizzo"] <= collaudo < b["indirizzo"] + len(b["dati"])]
    verifica(not tocca, "il file scrive sopra i dati di collaudo di fabbrica")
    print("  i dati di collaudo a 508 KB restano intatti  ok")

    # ------------------------------------------------------------------
    titolo("4. Dentro l'archivio c'e' il programma")

    archivio = memoria_da(blocchi, inizio_archivio, c.ARCHIVIO_BYTE)
    from littlefs import LittleFS
    fs = LittleFS(block_size=c.BLOCCO, block_count=c.ARCHIVIO_BYTE // c.BLOCCO,
                  prog_size=c.SCRITTURA, read_size=c.LETTURA, mount=False)
    fs.context.buffer[:] = bytearray(archivio)
    try:
        fs.mount()
        montato = True
    except Exception as e:
        montato = False
        print("  ERRORE nel montare l'archivio: %r" % e)
    verifica(montato, "l'archivio ricostruito dal file non si monta")

    if montato:
        dentro = sorted(fs.listdir("/"))
        verifica(dentro == sorted(c.FILE_DISPOSITIVO),
                 "i file nell'archivio non sono quelli attesi: %s" % dentro)
        uguali = 0
        for nome in dentro:
            with fs.open(nome, "rb") as f:
                dallarchivio = f.read()
            with open(nome, "rb") as f:
                suldisco = f.read()
            if dallarchivio == suldisco:
                uguali += 1
            else:
                verifica(False, "%s dentro il file e' diverso da quello sul disco" % nome)
        print("  %d file, tutti identici a quelli sul disco .. ok" % uguali)

        # ------------------------------------------------------------------
        titolo("5. Le tre parole che il dispositivo mostrera'")

        # Lo stesso calcolo di impronta.py, ma fatto sui file letti
        # dall'archivio ricostruito: e' esattamente cio' che il dispositivo
        # si trovera' in casa dopo aver caricato questo file.
        h = hashlib.sha256()
        h.update(imp.immagine_flash(ufficiale))
        for nome in sorted(dentro):
            h.update(nome.encode())
            with fs.open(nome, "rb") as f:
                h.update(f.read())
        tre = imp.parole_da(h.digest())
        attese = imp.calcola_parole(ufficiale)[1]
        verifica(tre == attese,
                 "le tre parole non coincidono: %s invece di %s" % (tre, attese))
        print("  %s" % "  ".join(w.upper() for w in tre))
        print("  coincidono con prepara_impronta.py ......... ok")

    # ------------------------------------------------------------------
    print()
    print("=" * 62)
    if _falliti:
        print("  %d CONTROLLI FALLITI su %d"
              % (len(_falliti), len(_falliti) + _passati[0]))
        print("=" * 62)
        for f in _falliti:
            print("  - %s" % f)
        sys.exit(1)
    print("  TUTTI I %d CONTROLLI SUPERATI" % _passati[0])
    print("=" * 62)
    print()
    print("  Il file contiene MicroPython intatto e il programma, e dopo")
    print("  averlo caricato il dispositivo deve mostrare le tre parole")
    print("  qui sopra. Resta da provarlo sull'hardware vero.")


if __name__ == "__main__":
    main()
