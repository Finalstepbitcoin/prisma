#!/usr/bin/env python3
"""
parla_col_pico.py  --  Final Step Bitcoin / Checksum Tool

Piccolo strumento per parlare con il Pico senza installare NIENTE.
Usa solo la libreria standard di Python (termios, select): niente pip,
niente programmi di terze parti.

A cosa serve:
    - eseguire un comando sulla scheda e vederne il risultato
    - copiare un file dal Mac alla scheda

Uso:
    python3 parla_col_pico.py info
    python3 parla_col_pico.py esegui "print(1+1)"
    python3 parla_col_pico.py copia bip39_checksum.py
    python3 parla_col_pico.py elenco

Come funziona: MicroPython espone una "REPL grezza" (raw REPL), un canale
pensato apposta per essere pilotato da un programma invece che da una persona.
Si entra con CTRL-A, si manda il codice, si esegue con CTRL-D.
"""

import glob
import os
import select
import sys
import termios
import time

CTRL_A = b"\x01"   # entra in REPL grezza
CTRL_B = b"\x02"   # torna alla REPL normale
CTRL_C = b"\x03"   # interrompi il programma in corso
CTRL_D = b"\x04"   # esegui


def trova_porta():
    porte = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not porte:
        print("ERRORE: nessuna scheda collegata.")
        print("Controlla il cavo, e che sia un cavo DATI e non solo da ricarica.")
        sys.exit(1)
    return porte[0]


class Pico:
    def __init__(self, porta=None):
        self.porta = porta or trova_porta()
        self.fd = os.open(self.porta, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self._modo_grezzo()

    def _modo_grezzo(self):
        """Toglie ogni elaborazione del testo: i byte passano come sono."""
        a = termios.tcgetattr(self.fd)
        a[0] = 0                       # iflag
        a[1] = 0                       # oflag
        a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        a[3] = 0                       # lflag: niente eco, niente righe
        a[6][termios.VMIN] = 0
        a[6][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW, a)

    def scrivi(self, dati):
        while dati:
            select.select([], [self.fd], [], 2)
            n = os.write(self.fd, dati[:256])
            dati = dati[n:]
            time.sleep(0.002)

    def leggi_fino(self, atteso, scadenza=10):
        """Legge finche' non arriva la sequenza attesa (o scade il tempo)."""
        buf = b""
        limite = time.time() + scadenza
        while time.time() < limite:
            pronti, _, _ = select.select([self.fd], [], [], 0.05)
            if pronti:
                pezzo = os.read(self.fd, 4096)
                if pezzo:
                    buf += pezzo
                    if atteso in buf:
                        return buf
        raise TimeoutError(
            "la scheda non ha risposto entro %d secondi.\n"
            "Ricevuto finora: %r" % (scadenza, buf[-200:]))

    def riavvia(self):
        """
        Riavvio "morbido": azzera la memoria di lavoro e scarica tutti i
        moduli, come se la scheda fosse appena accesa. Non tocca i file.
        Serve perche' fra un comando e l'altro la scheda NON riparte da sola:
        senza questo, le prove si portano dietro la memoria di quelle prima.
        """
        self.scrivi(CTRL_B)          # esci dalla REPL grezza
        time.sleep(0.1)
        self.scrivi(CTRL_D)          # riavvio morbido
        time.sleep(1.5)
        # svuota quello che la scheda ha stampato riavviandosi
        while True:
            pronti, _, _ = select.select([self.fd], [], [], 0.3)
            if not pronti:
                break
            os.read(self.fd, 4096)
        self.entra_grezza()

    def entra_grezza(self):
        self.scrivi(CTRL_C)      # ferma qualunque cosa stia girando
        time.sleep(0.1)
        self.scrivi(CTRL_C)
        time.sleep(0.1)
        self.scrivi(CTRL_A)
        self.leggi_fino(b"raw REPL; CTRL-B to exit\r\n>")

    def esci_grezza(self):
        self.scrivi(CTRL_B)

    def esegui(self, codice, scadenza=180):
        """Esegue codice sulla scheda e restituisce (uscita, errore)."""
        self.scrivi(codice.encode("utf-8"))
        self.scrivi(CTRL_D)
        risposta = self.leggi_fino(b"\x04>", scadenza)
        if not risposta.startswith(b"OK"):
            raise RuntimeError("la scheda ha rifiutato il codice: %r" % risposta[:120])
        corpo = risposta[2:]
        pezzi = corpo.split(b"\x04")
        uscita = pezzi[0].decode("utf-8", "replace")
        errore = pezzi[1].decode("utf-8", "replace") if len(pezzi) > 1 else ""
        return uscita, errore

    def chiudi(self):
        try:
            self.esci_grezza()
        finally:
            os.close(self.fd)


def comando_esegui(pico, codice):
    uscita, errore = pico.esegui(codice)
    if uscita:
        print(uscita, end="")
    if errore.strip():
        print("\n--- ERRORE SULLA SCHEDA ---")
        print(errore.strip())
        return 1
    return 0


def comando_info(pico):
    codice = (
        "import sys, gc, os, machine\n"
        "gc.collect()\n"
        "print('MicroPython :', '.'.join(str(x) for x in sys.implementation.version))\n"
        "print('piattaforma :', sys.platform)\n"
        "print('frequenza   : %d MHz' % (machine.freq()//1000000))\n"
        "print('RAM libera  : %d KB' % (gc.mem_free()//1024))\n"
        "s = os.statvfs('/')\n"
        "print('disco libero: %d KB su %d KB' % (s[0]*s[3]//1024, s[0]*s[2]//1024))\n"
    )
    return comando_esegui(pico, codice)


def comando_elenco(pico):
    return comando_esegui(pico, "import os\nfor f in os.listdir('/'): print(f)\n")


def comando_copia(pico, percorso):
    nome = os.path.basename(percorso)
    with open(percorso, "rb") as f:
        dati = f.read()

    print("Copio %s (%d byte) sulla scheda..." % (nome, len(dati)))
    uscita, errore = pico.esegui("f = open(%r, 'wb')\n" % nome)
    if errore.strip():
        print(errore)
        return 1

    PEZZO = 512
    inviati = 0
    for i in range(0, len(dati), PEZZO):
        blocco = dati[i:i + PEZZO]
        uscita, errore = pico.esegui("f.write(%r)\n" % blocco)
        if errore.strip():
            print("\nERRORE durante la scrittura:", errore.strip())
            return 1
        inviati += len(blocco)
        print("\r  %d%%" % (100 * inviati // len(dati)), end="", flush=True)
    print()

    pico.esegui("f.close()\n")

    # controprova: rileggo la dimensione dalla scheda
    uscita, _ = pico.esegui("import os\nprint(os.stat(%r)[6])\n" % nome)
    scritti = int(uscita.strip())
    if scritti != len(dati):
        print("ERRORE: sulla scheda ci sono %d byte invece di %d" % (scritti, len(dati)))
        return 1
    print("Copiato e verificato: %d byte." % scritti)
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    pico = Pico()
    print("Scheda su %s\n" % pico.porta)
    try:
        pico.entra_grezza()
        cmd = sys.argv[1]
        if cmd == "riavvia":
            pico.riavvia()
            print("Scheda riavviata: memoria pulita, file intatti.")
            return 0
        if "--pulito" in sys.argv:
            pico.riavvia()
            sys.argv.remove("--pulito")
        if cmd == "info":
            return comando_info(pico)
        if cmd == "elenco":
            return comando_elenco(pico)
        if cmd == "esegui":
            return comando_esegui(pico, sys.argv[2] + "\n")
        if cmd == "copia":
            return comando_copia(pico, sys.argv[2])
        if cmd == "lancia":
            # avvia del codice che NON finisce (tipo l'interfaccia) e lascia
            # la scheda a girare per conto suo, senza aspettare la fine
            pico.scrivi((sys.argv[2] + "\n").encode("utf-8"))
            pico.scrivi(CTRL_D)
            time.sleep(1)
            print("Avviato sulla scheda. Guarda lo schermo.")
            print("(per riprendere il controllo basta rilanciare un altro comando)")
            return 0
        print("comando sconosciuto: %s" % cmd)
        return 1
    finally:
        pico.chiudi()


if __name__ == "__main__":
    sys.exit(main())
