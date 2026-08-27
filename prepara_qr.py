#!/usr/bin/env python3
"""
prepara_qr.py  --  Final Step Bitcoin / Prisma

Disegna il codice QR del canale YouTube e lo salva come immagine gia' pronta
in  qr_canale.py .

QUESTO SCRIPT GIRA SOLO SUL MAC, una volta sola.

PERCHE' COSI' E NON DIRETTAMENTE SUL DISPOSITIVO
Disegnare un codice QR richiede una libreria intera (correzione d'errore,
mascheratura, tabelle). Metterla nel firmware significherebbe centinaia di
righe in piu' da verificare, per disegnare sempre la stessa identica
immagine. Meglio calcolarla una volta qui e portarsi dietro solo il
risultato: un centinaio di byte di dati, zero codice.

Serve la libreria segno (BSD, nessuna dipendenza), installata nell'ambiente
isolato .venv-strumenti che NON fa parte del progetto.

Uso:
    .venv-strumenti/bin/python prepara_qr.py
"""

import hashlib
import sys

try:
    import segno
except ImportError:
    print("ERRORE: manca segno. Installalo nell'ambiente isolato:")
    print("    python3 -m venv .venv-strumenti")
    print("    .venv-strumenti/bin/pip install segno")
    sys.exit(1)

INDIRIZZO = "https://www.youtube.com/@final_step_bitcoin"
USCITA = "qr_canale.py"


def main():
    # correzione d'errore media: sopporta bene un po' di sporco sullo
    # schermo e resta piccolo abbastanza da leggersi da 240 pixel
    qr = segno.make(INDIRIZZO, error="m")
    righe = ["".join("1" if m else "0" for m in riga) for riga in qr.matrix]
    lato = len(righe)

    print("indirizzo : %s" % INDIRIZZO)
    print("versione  : %s   correzione: %s" % (qr.version, qr.error.upper()))
    print("lato      : %d moduli" % lato)

    # controlli strutturali: i tre quadrati d'angolo devono esserci
    def quadrato(r0, c0):
        return all(righe[r0 + r][c0 + c] == ("1" if
                   (r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4))
                   else "0") for r in range(7) for c in range(7))

    angoli = (quadrato(0, 0), quadrato(0, lato - 7), quadrato(lato - 7, 0))
    if not all(angoli):
        print("ERRORE: i quadrati di riferimento non sono al loro posto.")
        sys.exit(1)
    print("angoli    : tutti e tre corretti")

    if any(len(r) != lato for r in righe):
        print("ERRORE: la matrice non e' quadrata.")
        sys.exit(1)

    impronta = hashlib.sha256("".join(righe).encode()).hexdigest()

    testo = []
    testo.append('"""')
    testo.append("Codice QR del canale - GENERATO AUTOMATICAMENTE, non modificare a mano.")
    testo.append("")
    testo.append("Indirizzo: %s" % INDIRIZZO)
    testo.append("Versione:  %s, correzione %s, %d moduli di lato"
                 % (qr.version, qr.error.upper(), lato))
    testo.append("SHA-256:   %s" % impronta)
    testo.append("")
    testo.append("Ogni riga e' fatta di 1 (modulo scuro) e 0 (modulo chiaro).")
    testo.append("Per rigenerarlo:  .venv-strumenti/bin/python prepara_qr.py")
    testo.append('"""')
    testo.append("")
    testo.append('INDIRIZZO = "%s"' % INDIRIZZO)
    testo.append("LATO = %d" % lato)
    testo.append("MODULI = (")
    for r in righe:
        testo.append('    "%s",' % r)
    testo.append(")")
    testo.append("")

    with open(USCITA, "w", encoding="utf-8") as f:
        f.write("\n".join(testo))

    print("SHA-256   : %s" % impronta)
    print("generato  : %s" % USCITA)

    # anteprima a terminale, per vedere subito se ha senso
    print("\nanteprima (due moduli per carattere):\n")
    print("  " + "█" * (lato + 4) * 1)
    for r in righe:
        print("  ██" + "".join("  " if c == "1" else "██" for c in r)
              .replace("", "") + "██")
    print("  " + "█" * (lato + 4) * 1)
    print("\nInquadralo col telefono per controllare che porti al canale.")


if __name__ == "__main__":
    main()
