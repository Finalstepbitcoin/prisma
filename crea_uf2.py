#!/usr/bin/env python3
"""
crea_uf2.py  --  Final Step Bitcoin / Prisma

Costruisce UN SOLO file da trascinare sul dispositivo, che contiene sia
MicroPython sia il programma.

GIRA SUL MAC. Serve la libreria littlefs-python nell'ambiente isolato
.venv-strumenti (vedi LEGGIMI-uf2.md).

Uso:
    .venv-strumenti/bin/python crea_uf2.py

PERCHE' ESISTE
Fino a ieri chi voleva installarsi il software da solo doveva: azzerare la
memoria, caricare MicroPython, installare Python sul computer, aprire il
terminale e lanciare tre script che copiano dieci file uno per uno.
Con questo file: tiene premuto BOOTSEL, collega il cavo, trascina un file.
Trenta secondi, nessun programma da installare.

COME E' FATTO UN FILE .uf2
Non e' un formato misterioso: e' un elenco di blocchi da 512 byte, ognuno
dei quali dice "scrivi questi 256 byte a questo indirizzo". Il caricatore
del Pico li scrive uno per uno. Noi ne mettiamo insieme due gruppi:

    0x10000000  MicroPython           (320 KB, presi dal .uf2 ufficiale)
    0x10100000  l'archivio coi file   (costruito qui sul Mac)

I due gruppi non si toccano: il firmware finisce a 320 KB, l'archivio
comincia a 1024 KB. In mezzo, a 508 KB, ci sono i dati di collaudo che il
Raspberry Pi scrive in fabbrica: non li tocchiamo ne' li misuriamo (e' la
stessa ragione per cui l'impronta si ferma a 448 KB).

I PARAMETRI DELL'ARCHIVIO NON SONO INVENTATI
Vengono dalla sorgente di MicroPython, e devono combaciare ESATTAMENTE,
altrimenti il dispositivo si accende e non trova niente:

  ports/rp2/boards/RPI_PICO2/mpconfigboard.cmake
      MICROPY_HW_FLASH_STORAGE_BYTES 3145728        -> 3 MB di archivio
  ports/rp2/rp2_flash.c
      MICROPY_HW_FLASH_STORAGE_BASE (PICO_FLASH_SIZE_BYTES - STORAGE_BYTES)
                                                    -> comincia a 4MB-3MB = 1MB
      BLOCK_SIZE_BYTES (FLASH_SECTOR_SIZE)          -> blocchi da 4096 byte
  ports/rp2/modules/_boot.py
      vfs.VfsLfs2(bdev, progsize=256)               -> scritture da 256 byte
"""

import hashlib
import os
import re
import struct
import sys

# --- i valori presi dalla sorgente di MicroPython (vedi sopra) -------------
INIZIO_FLASH = 0x10000000
ARCHIVIO_INIZIO = 1024 * 1024          # 1 MB dall'inizio della memoria
ARCHIVIO_BYTE = 3145728                # 3 MB
BLOCCO = 4096
SCRITTURA = 256                        # progsize
LETTURA = 32                           # readsize, il valore predefinito

# --- il formato .uf2 -------------------------------------------------------
UF2_MAGIC0 = 0x0A324655
UF2_MAGIC1 = 0x9E5D5157
UF2_MAGIC_FINE = 0x0AB16F30
UF2_FLAG_FAMIGLIA = 0x00002000
CARICO = 256                           # byte utili per blocco

# --- cosa va dentro --------------------------------------------------------
# La stessa lista di installa.py e prepara_impronta.py.
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

# La versione NON si scrive qui: si legge da interfaccia.py, che e' quella
# che il dispositivo mostra sullo schermo. Tenendone due copie, prima o poi
# il nome del file e la scritta sullo schermo direbbero numeri diversi.
VERSIONE = re.search(r'VERSIONE\s*=\s*"([^"]+)"',
                     open("interfaccia.py").read()).group(1)


# ---------------------------------------------------------------------------
# 1. l'archivio
# ---------------------------------------------------------------------------

def costruisci_archivio():
    """
    L'immagine dell'archivio, con dentro i dieci file.

    Nessuna data di modifica viene scritta: cosi' l'immagine e' sempre
    identica a parita' di file, e chiunque puo' rifarla e ottenere lo
    stesso identico risultato. E' la stessa ragione per cui il dispositivo
    non scrive niente da solo.
    """
    from littlefs import LittleFS

    fs = LittleFS(block_size=BLOCCO,
                  block_count=ARCHIVIO_BYTE // BLOCCO,
                  prog_size=SCRITTURA,
                  read_size=LETTURA,
                  mount=False)
    fs.format()
    fs.mount()
    for nome in FILE_DISPOSITIVO:
        with open(nome, "rb") as f:
            dati = f.read()
        with fs.open(nome, "wb") as f:
            f.write(dati)
        print("   %-20s %7d byte" % (nome, len(dati)))
    fs.unmount()
    return bytes(fs.context.buffer)


# ---------------------------------------------------------------------------
# 2. il file .uf2
# ---------------------------------------------------------------------------

def leggi_uf2(percorso):
    """I blocchi del .uf2 ufficiale di MicroPython: (indirizzo, dati, famiglia)."""
    with open(percorso, "rb") as f:
        dati = f.read()
    if len(dati) % 512:
        sys.exit("ERRORE: %s non e' un .uf2 valido." % percorso)
    fuori = []
    for i in range(len(dati) // 512):
        b = dati[i * 512:(i + 1) * 512]
        m0, m1, bandiere, indirizzo, quanti = struct.unpack("<5I", b[:20])
        famiglia = struct.unpack("<I", b[28:32])[0]
        if m0 != UF2_MAGIC0 or m1 != UF2_MAGIC1:
            continue
        # Le bandiere vanno CONSERVATE, non ricostruite. Il primo blocco dei
        # .uf2 per RP2350 ha anche il bit 0x8000 ("qui dentro ci sono tag di
        # estensione"): riscrivendolo come un blocco qualunque si perde, e il
        # caricatore del Pico non riconosce piu' l'immagine e non riavvia.
        numero, totale = struct.unpack("<2I", b[20:28])
        fuori.append((indirizzo, b[32:32 + quanti], famiglia, bandiere,
                      numero, totale))
    return fuori


def scrivi_uf2(blocchi, percorso):
    """
    Scrive i blocchi rinumerandoli tutti.

    ATTENZIONE, E' IL PUNTO DELICATO: ogni blocco .uf2 porta scritto il
    proprio numero e QUANTI sono in tutto. Accodando semplicemente due file
    uno all'altro, i blocchi di MicroPython continuerebbero a dichiarare il
    totale vecchio, e il caricatore del Pico crederebbe di aver finito a
    meta' strada.

    MA LA NUMERAZIONE NON E' UNICA: il caricatore tiene un conto separato
    per ogni "famiglia" di blocchi. Il .uf2 di MicroPython per RP2350 ne ha
    due: un blocco solo di famiglia ABSOLUTE (che dichiara un totale di 2, e
    resta apposta incompleto) e 1282 blocchi della famiglia del chip. Se si
    rinumera tutto in un'unica sequenza, come si faceva prima, la famiglia
    del chip non riceve mai il suo blocco numero 0 e quella ABSOLUTE aspetta
    blocchi che non arriveranno: nessuna delle due si completa e il
    dispositivo NON si riavvia mai. Provato sull'hardware il 27/08/2026.

    Quindi: le famiglie a cui aggiungiamo blocchi si rinumerano daccapo,
    quelle che restano come sono non si toccano.
    """
    nuove = {b[2] for b in blocchi if b[4] is None}
    quanti_per_famiglia = {}
    for b in blocchi:
        quanti_per_famiglia[b[2]] = quanti_per_famiglia.get(b[2], 0) + 1
    contatore = {}
    with open(percorso, "wb") as f:
        for indirizzo, dati, famiglia, bandiere, numero, totale in blocchi:
            if famiglia in nuove:
                numero = contatore.get(famiglia, 0)
                contatore[famiglia] = numero + 1
                totale = quanti_per_famiglia[famiglia]
            intestazione = struct.pack(
                "<8I", UF2_MAGIC0, UF2_MAGIC1, bandiere,
                indirizzo, len(dati), numero, totale, famiglia)
            f.write(intestazione + dati.ljust(476, b"\x00")
                    + struct.pack("<I", UF2_MAGIC_FINE))
    return len(blocchi)


def blocchi_da(immagine, indirizzo_base, famiglia):
    """
    Spezza l'immagine dell'archivio in blocchi da 256 byte, SALTANDO quelli
    ancora vergini (tutti 0xFF, cioe' memoria mai scritta).

    Si puo' saltare perche' ogni blocco .uf2 si porta dietro il proprio
    indirizzo: non devono essere uno di fila all'altro. E conviene, perche'
    littlefs sparge i file in giro per l'archivio invece di metterli tutti
    all'inizio - lo fa apposta, per non consumare sempre le stesse celle di
    memoria. Scrivendo tutto il tratto dal primo all'ultimo blocco usato ci
    porteremmo dietro 2,4 MB di vuoto: cosi' invece si scrivono solo i
    224 KB che contengono davvero qualcosa.

    E' sicuro anche rispetto a un'installazione precedente, per due motivi.
    Il caricatore del Pico cancella l'intero settore da 4096 byte prima di
    scriverne anche un solo pezzo, quindi i settori toccati restano puliti.
    E l'elenco dei file, che sta nei primi due blocchi, viene riscritto per
    intero: qualunque file di prima diventa irraggiungibile, e lo spazio che
    occupava risulta libero.
    """
    fuori = []
    for scarto in range(0, len(immagine), CARICO):
        pezzo = immagine[scarto:scarto + CARICO]
        if pezzo == b"\xff" * CARICO:
            continue
        fuori.append((indirizzo_base + scarto, pezzo, famiglia,
                      UF2_FLAG_FAMIGLIA, None, None))
    return fuori


def main():
    import prepara_impronta as imp

    print("=" * 62)
    print("  UN SOLO FILE DA TRASCINARE")
    print("=" * 62)

    uf2_micropython = imp.verifica_uf2(imp.trova_uf2())
    print("\nMicroPython : %s" % uf2_micropython)

    mancanti = [f for f in FILE_DISPOSITIVO if not os.path.exists(f)]
    if mancanti:
        sys.exit("ERRORE: mancano dei file: %s" % ", ".join(mancanti))

    print("\nCostruisco l'archivio con dentro il programma:")
    immagine = costruisci_archivio()

    blocchi_firmware = leggi_uf2(uf2_micropython)
    famiglia = next(b[2] for b in blocchi_firmware
                    if b[2] == imp.FAMIGLIA_RP2350)
    blocchi_archivio = blocchi_da(immagine, INIZIO_FLASH + ARCHIVIO_INIZIO,
                                  famiglia)

    uscita = "prisma-%s.uf2" % VERSIONE
    totale = scrivi_uf2(blocchi_firmware + blocchi_archivio, uscita)

    peso = os.path.getsize(uscita)
    with open(uscita, "rb") as f:
        impronta_file = hashlib.sha256(f.read()).hexdigest()

    print("\nfirmware    : %d blocchi (MicroPython, non toccato)"
          % len(blocchi_firmware))
    print("archivio    : %d blocchi (%d KB dei %d KB disponibili)"
          % (len(blocchi_archivio), len(blocchi_archivio) * CARICO // 1024,
             ARCHIVIO_BYTE // 1024))
    print("\nGENERATO: %s  (%d KB, %d blocchi in tutto)"
          % (uscita, peso // 1024, totale))
    print("SHA-256 : %s" % impronta_file)
    print("\nSi carica cosi': tieni premuto BOOTSEL mentre colleghi il cavo,")
    print("compare un disco, ci trascini sopra questo file. Basta.")


if __name__ == "__main__":
    main()
