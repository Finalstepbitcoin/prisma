#!/usr/bin/env python3
"""
prepara_qr_guida.py  --  Final Step Bitcoin / Sintesi

Disegna il codice QR stampato sulla guida (facciata 2, riquadro della
verifica del firmware) e lo salva come immagine SVG gia' pronta in
    qr-verifica.svg.txt
da incollare dentro sorgente.html al posto del vecchio <svg class="qr">.

GIRA SOLO SUL MAC, e solo quando cambia l'indirizzo.

PERCHE' IL QR VA STAMPATO E NON MOSTRATO DAL DISPOSITIVO
Un firmware manomesso mostrerebbe sullo schermo un indirizzo falso, e
manderebbe chi verifica su una pagina scritta da chi l'ha manomesso. Sulla
carta questo non puo' succedere: il foglio non lo puo' riscrivere nessuno.

Serve la libreria segno (BSD), installata nell'ambiente isolato
.venv-strumenti della cartella del progetto, che NON fa parte del progetto.

Uso:
    ../.venv-strumenti/bin/python prepara_qr_guida.py
"""

import os
import sys

try:
    import segno
except ImportError:
    print("ERRORE: manca segno. Installalo nell'ambiente isolato:")
    print("    cd ..")
    print("    python3 -m venv .venv-strumenti")
    print("    .venv-strumenti/bin/pip install segno")
    sys.exit(1)

# L'UNICO punto da cambiare se l'indirizzo della pagina cambia. Ricordati
# di aggiornare anche la scritta sotto il QR dentro sorgente.html.
INDIRIZZO = "https://github.com/Finalstepbitcoin/sintesi"
USCITA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "qr-verifica.svg.txt")


def main():
    # correzione d'errore media: sopporta bene la stampa e un po' di usura
    # del foglio, e resta piccolo abbastanza da stare in 26 mm
    qr = segno.make(INDIRIZZO, error="m")
    righe = ["".join("1" if m else "0" for m in riga) for riga in qr.matrix]
    lato = len(righe)

    print("indirizzo : %s" % INDIRIZZO)
    print("versione  : %s   correzione: %s" % (qr.version, qr.error.upper()))
    print("lato      : %d moduli" % lato)

    # controllo strutturale: i tre quadrati d'angolo devono esserci
    def quadrato(r0, c0):
        return all(righe[r0 + r][c0 + c] == ("1" if
                   (r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4))
                   else "0") for r in range(7) for c in range(7))

    if not all((quadrato(0, 0), quadrato(0, lato - 7), quadrato(lato - 7, 0))):
        print("ERRORE: i quadrati di riferimento non sono al loro posto.")
        sys.exit(1)
    print("angoli    : tutti e tre corretti")

    # un rettangolo per ogni sequenza di moduli scuri: l'SVG resta piccolo
    d = []
    for y, riga in enumerate(righe):
        x = 0
        while x < lato:
            if riga[x] == "1":
                fine = x
                while fine < lato and riga[fine] == "1":
                    fine += 1
                d.append("M%d %dh%dv1h-%dz" % (x, y, fine - x, fine - x))
                x = fine
            else:
                x += 1

    # il margine chiaro di 2 moduli attorno al codice lo vuole lo standard:
    # senza, molti telefoni non lo leggono
    lato_tot = lato + 4
    svg = ('<svg class="qr" viewBox="-2 -2 %d %d" '
           'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
           '<rect x="-2" y="-2" width="%d" height="%d" fill="#fff"/>'
           '<path fill="#000" d="%s"/></svg>'
           % (lato_tot, lato_tot, lato_tot, lato_tot, "".join(d)))

    with open(USCITA, "w", encoding="utf-8") as f:
        f.write(svg)

    print("generato  : %s (%d byte)" % (USCITA, len(svg)))
    print()
    print("Ora incolla il contenuto di quel file dentro sorgente.html,")
    print("al posto del vecchio <svg class=\"qr\">...</svg>, e rilancia build.sh.")
    print("Poi INQUADRALO COL TELEFONO dal PDF stampato: e' l'unico controllo")
    print("che conta davvero.")


if __name__ == "__main__":
    main()
