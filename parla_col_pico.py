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
    python3 parla_col_pico.py verifica bip39_checksum.py
    python3 parla_col_pico.py elenco

Come funziona: MicroPython espone una "REPL grezza" (raw REPL), un canale
pensato apposta per essere pilotato da un programma invece che da una persona.
Si entra con CTRL-A, si manda il codice, si esegue con CTRL-D.
"""

import glob
import hashlib
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


def _cancella_su_scheda(pico, nome):
    """Best-effort: non importa se il file non c'era gia'."""
    pico.esegui("import os\ntry:\n    os.remove(%r)\nexcept OSError:\n    pass\n" % nome)


def comando_copia(pico, percorso):
    """
    Copia con un file temporaneo + verifica del CONTENUTO + scambio finale.

    Perche' non basta scrivere direttamente sul nome vero: se il cavo si
    stacca o il trasferimento si interrompe a meta', il file di destinazione
    resterebbe troncato. Scrivendo su un nome temporaneo e spostandolo sopra
    solo DOPO che il contenuto e' stato verificato byte per byte, un
    trasferimento interrotto lascia intatta l'ultima versione buona.

    E perche' l'hash e non solo la dimensione: due file della stessa
    lunghezza possono avere contenuto diverso (un pezzo corrotto in
    trasmissione, per esempio). Solo un confronto del contenuto lo rileva.
    """
    nome = os.path.basename(percorso)
    temporaneo = "." + nome + ".tmp"
    with open(percorso, "rb") as f:
        dati = f.read()
    impronta_attesa = hashlib.sha256(dati).hexdigest()

    print("Copio %s (%d byte) sulla scheda..." % (nome, len(dati)))
    uscita, errore = pico.esegui("f = open(%r, 'wb')\n" % temporaneo)
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
            pico.esegui("f.close()\n")
            _cancella_su_scheda(pico, temporaneo)
            return 1
        inviati += len(blocco)
        print("\r  %d%%" % (100 * inviati // len(dati)), end="", flush=True)
    print()
    pico.esegui("f.close()\n")

    # confronto del CONTENUTO, calcolato sulla scheda: non solo la
    # dimensione, che una corruzione a parita' di byte non rileverebbe
    codice_hash = (
        "import hashlib\n"
        "h = hashlib.sha256()\n"
        "with open(%r, 'rb') as fv:\n"
        "    while True:\n"
        "        pezzo = fv.read(1024)\n"
        "        if not pezzo:\n"
        "            break\n"
        "        h.update(pezzo)\n"
        "print(h.digest().hex())\n"
    ) % temporaneo
    uscita, errore = pico.esegui(codice_hash)
    if errore.strip():
        print("ERRORE calcolando l'impronta sulla scheda:", errore.strip())
        _cancella_su_scheda(pico, temporaneo)
        return 1
    impronta_scheda = uscita.strip()
    if impronta_scheda != impronta_attesa:
        print("ERRORE: impronta diversa dopo la copia.")
        print("  atteso : %s" % impronta_attesa)
        print("  scheda : %s" % impronta_scheda)
        _cancella_su_scheda(pico, temporaneo)
        return 1

    # solo ORA, con contenuto verificato, si sostituisce il file vero: se
    # la corrente si interrompe qui, nel peggiore dei casi resta il file
    # temporaneo (gia' valido) accanto a quello vecchio, mai un file a meta'
    codice_scambio = (
        "import os\n"
        "try:\n"
        "    os.remove(%r)\n"
        "except OSError:\n"
        "    pass\n"
        "os.rename(%r, %r)\n"
    ) % (nome, temporaneo, nome)
    uscita, errore = pico.esegui(codice_scambio)
    if errore.strip():
        print("ERRORE sostituendo il file:", errore.strip())
        return 1

    print("Copiato e verificato: %d byte, SHA-256 %s..." % (len(dati), impronta_attesa[:12]))
    return 0


def comando_verifica(pico, percorso):
    """
    Confronta l'hash del file sulla scheda con quello del file sul Mac,
    SENZA ritrasferire il contenuto. Usato da installa.py per la verifica
    finale: prova che ogni file installato corrisponde davvero a quello
    atteso, non solo che qualcosa con quel nome esiste.
    """
    nome = os.path.basename(percorso)
    with open(percorso, "rb") as f:
        attesa = hashlib.sha256(f.read()).hexdigest()

    codice = (
        "import hashlib, os\n"
        "try:\n"
        "    os.stat(%r)\n"
        "except OSError:\n"
        "    print('MANCANTE')\n"
        "else:\n"
        "    h = hashlib.sha256()\n"
        "    with open(%r, 'rb') as fv:\n"
        "        while True:\n"
        "            pezzo = fv.read(1024)\n"
        "            if not pezzo:\n"
        "                break\n"
        "            h.update(pezzo)\n"
        "    print(h.digest().hex())\n"
    ) % (nome, nome)
    uscita, errore = pico.esegui(codice)
    if errore.strip():
        print("DIVERSO   %-20s (errore: %s)" % (nome, errore.strip()))
        return 1

    trovata = uscita.strip()
    if trovata == "MANCANTE":
        print("MANCANTE  %s" % nome)
        return 1
    if trovata != attesa:
        print("DIVERSO   %s" % nome)
        return 1
    print("ok        %s" % nome)
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
        if cmd == "verifica":
            return comando_verifica(pico, sys.argv[2])
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
