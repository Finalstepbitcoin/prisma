#!/usr/bin/env python3
"""
parla_col_pico.py  --  Final Step Bitcoin / Prisma

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

    python3 parla_col_pico.py prepara bip39_checksum.py    (copia SENZA attivare)
    python3 parla_col_pico.py attiva bip39_checksum.py main.py ...   (attiva in blocco)
    Usati da installa.py per installare piu' file con un'unica finestra
    di rischio breve invece che una per file: vedi comando_prepara e
    comando_attiva qui sotto.

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


def _trasferisci_e_verifica(pico, percorso):
    """
    Scrive il contenuto sotto nome temporaneo e ne verifica il CONTENUTO
    (non solo la dimensione: un pezzo corrotto in trasmissione puo' dare
    un file della lunghezza giusta ma sbagliato) confrontando l'hash
    calcolato sulla scheda con quello del file sul Mac.

    NON sostituisce ancora il file vero: quello lo fa _codice_scambio(),
    chiamato da chi usa questa funzione. Tenerli separati e' cio' che
    permette a installa.py di preparare e verificare TUTTI i file prima
    di toccarne anche uno solo di quelli attivi (vedi comando_attiva).

    Restituisce (0, nome, temporaneo) se e' andato tutto bene,
    (1, None, None) altrimenti.
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
        return 1, None, None

    PEZZO = 512
    inviati = 0
    for i in range(0, len(dati), PEZZO):
        blocco = dati[i:i + PEZZO]
        uscita, errore = pico.esegui("f.write(%r)\n" % blocco)
        if errore.strip():
            print("\nERRORE durante la scrittura:", errore.strip())
            pico.esegui("f.close()\n")
            _cancella_su_scheda(pico, temporaneo)
            return 1, None, None
        inviati += len(blocco)
        print("\r  %d%%" % (100 * inviati // len(dati)), end="", flush=True)
    print()
    pico.esegui("f.close()\n")

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
        return 1, None, None
    impronta_scheda = uscita.strip()
    if impronta_scheda != impronta_attesa:
        print("ERRORE: impronta diversa dopo la copia.")
        print("  atteso : %s" % impronta_attesa)
        print("  scheda : %s" % impronta_scheda)
        _cancella_su_scheda(pico, temporaneo)
        return 1, None, None

    print("Verificato: %d byte, SHA-256 %s..." % (len(dati), impronta_attesa[:12]))
    return 0, nome, temporaneo


def _codice_scambio(nome, temporaneo):
    """
    Il codice che sostituisce UN file col suo temporaneo gia' verificato.

    Prova PRIMA un rename diretto: su questo filesystem (littlefs) sostituisce
    da solo un file gia' esistente, senza bisogno di cancellarlo prima -
    quindi non c'e' mai un istante in cui il nome vero non esiste. Ricorre
    al remove-poi-rename SOLO se il rename diretto fallisse (per esempio su
    un filesystem che non lo permette): in quel caso, e solo in quel caso,
    c'e' una finestra minima e inevitabile fra le due operazioni.
    """
    return (
        "try:\n"
        "    os.rename(%r, %r)\n"
        "except OSError:\n"
        "    try:\n"
        "        os.remove(%r)\n"
        "    except OSError:\n"
        "        pass\n"
        "    os.rename(%r, %r)\n"
    ) % (temporaneo, nome, nome, temporaneo, nome)


def comando_copia(pico, percorso):
    """Copia un file e lo attiva subito. Per uso interattivo da terminale;
    installa.py usa invece prepara+attiva per installare piu' file insieme
    (vedi comando_prepara e comando_attiva)."""
    esito, nome, temporaneo = _trasferisci_e_verifica(pico, percorso)
    if esito != 0:
        return 1
    codice = "import os\n" + _codice_scambio(nome, temporaneo)
    uscita, errore = pico.esegui(codice)
    if errore.strip():
        print("ERRORE sostituendo il file:", errore.strip())
        return 1
    print("Copiato: %s" % nome)
    return 0


def comando_prepara(pico, percorso):
    """
    Copia e verifica un file SENZA attivarlo: resta sotto nome temporaneo.

    Usato da installa.py per preparare e verificare TUTTI i file prima di
    sostituire anche uno solo di quelli in uso: cosi' un'interruzione
    durante questa fase (che e' quella lunga, un trasferimento dati) non
    tocca nessun file attivo sul dispositivo. Vedi comando_attiva.
    """
    esito, _, _ = _trasferisci_e_verifica(pico, percorso)
    return esito


def comando_attiva(pico, nomi):
    """
    Sostituisce, IN UN SOLO COMANDO mandato alla scheda, ogni file vero
    con la sua versione temporanea gia' preparata da 'prepara'.

    E' un'operazione di filesystem (rinominare dei file), non un
    trasferimento dati: per tutti i file insieme dura una frazione di
    secondo, non secondi per ognuno come la copia. E' questo che riduce al
    minimo la finestra in cui staccare il cavo a meta' potrebbe lasciare
    una mescolanza di file vecchi e nuovi.

    ONESTA': non puo' azzerarla del tutto. Lo stesso cavo che porta i dati
    alimenta anche il dispositivo: se salta in quel preciso istante, il
    codice si ferma esattamente dov'e', e non c'e' modo di evitarlo via
    software. Quello che si puo' fare - e che questa funzione fa - e'
    rendere quell'istante il piu' breve possibile, e rendere il rilancio
    di installa.py dopo un'interruzione sempre sicuro (rifa' solo quello
    che manca, non danneggia quello che c'e' gia').
    """
    righe = ["import os"]
    for nome in nomi:
        temporaneo = "." + nome + ".tmp"
        righe.append(_codice_scambio(nome, temporaneo))
    righe.append("print('attivati %d file')" % len(nomi))
    codice = "\n".join(righe) + "\n"
    uscita, errore = pico.esegui(codice)
    if errore.strip():
        print("ERRORE nell'attivazione:", errore.strip())
        return 1
    print(uscita.strip())
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
    # su stderr, apposta: chi legge questo programma da terminale lo vede
    # comunque, ma chi lo chiama da un altro script (installa.py, per la
    # lista dei file sulla scheda) non si ritrova questa riga mescolata
    # all'output vero del comando
    print("Scheda su %s\n" % pico.porta, file=sys.stderr)
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
        if cmd == "prepara":
            return comando_prepara(pico, sys.argv[2])
        if cmd == "attiva":
            return comando_attiva(pico, sys.argv[2:])
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
