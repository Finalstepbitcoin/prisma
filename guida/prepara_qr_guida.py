#!/usr/bin/env python3
"""
prepara_qr_guida.py  --  Final Step Bitcoin / Prisma

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

# I QR stampati sulla guida. Per cambiarne uno basta cambiare l'indirizzo
# qui: ricordati di aggiornare anche la scritta sotto il QR dentro
# sorgente.html, che il generatore non tocca.
#
# La "classe" e' il nome del gruppo di stile nel foglio: il generatore la
# scrive dentro l'SVG, cosi' ogni QR si incolla al posto di quello vecchio
# cercando <svg class="NOME"> senza rischiare di scambiarli fra loro.
QR = [
    {
        "nome": "verifica",
        "classe": "qr",
        "indirizzo": "https://github.com/Finalstepbitcoin/prisma",
        "a_cosa_serve": "il codice sorgente, per verificare o ricompilare",
    },
    {
        "nome": "video",
        "classe": "qr-video",
        # Link diretto alla video guida. L'identificativo del video lo
        # assegna YouTube al caricamento e non cambia mai: passare da
        # privato a pubblico non lo tocca. Cambia SOLO se il video viene
        # cancellato e ricaricato - e con un QR gia' stampato quel video
        # non si cancella piu': si sostituisce il contenuto tenendo lo
        # stesso video.
        "indirizzo": "https://youtu.be/CFRjoe49_qk",
        "a_cosa_serve": "la video guida",
    },
]
CARTELLA = os.path.dirname(os.path.abspath(__file__))


def disegna(voce):
    """Un QR: dall'indirizzo all'SVG gia' pronto da incollare."""
    # correzione d'errore media: sopporta bene la stampa e un po' di usura
    # del foglio, e resta piccolo abbastanza da stare in 26 mm
    qr = segno.make(voce["indirizzo"], error="m")
    righe = ["".join("1" if m else "0" for m in riga) for riga in qr.matrix]
    lato = len(righe)

    print("\n%s  (%s)" % (voce["nome"].upper(), voce["a_cosa_serve"]))
    print("  indirizzo : %s" % voce["indirizzo"])
    print("  versione  : %s   correzione: %s   lato: %d moduli"
          % (qr.version, qr.error.upper(), lato))

    # controllo strutturale: i tre quadrati d'angolo devono esserci
    def quadrato(r0, c0):
        return all(righe[r0 + r][c0 + c] == ("1" if
                   (r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4))
                   else "0") for r in range(7) for c in range(7))

    if not all((quadrato(0, 0), quadrato(0, lato - 7), quadrato(lato - 7, 0))):
        print("  ERRORE: i quadrati di riferimento non sono al loro posto.")
        sys.exit(1)
    print("  angoli    : tutti e tre corretti")

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
    svg = ('<svg class="%s" viewBox="-2 -2 %d %d" '
           'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
           '<rect x="-2" y="-2" width="%d" height="%d" fill="#fff"/>'
           '<path fill="#000" d="%s"/></svg>'
           % (voce["classe"], lato_tot, lato_tot, lato_tot, lato_tot, "".join(d)))

    uscita = os.path.join(CARTELLA, "qr-%s.svg.txt" % voce["nome"])
    with open(uscita, "w", encoding="utf-8") as f:
        f.write(svg)
    print("  generato  : qr-%s.svg.txt (%d byte)" % (voce["nome"], len(svg)))


def main():
    for voce in QR:
        disegna(voce)
    print()
    print("Ora incolla ogni file dentro sorgente.html al posto del vecchio")
    print('<svg class="..."> con la STESSA classe, e rilancia build.sh.')
    print("Poi INQUADRALI COL TELEFONO dal PDF finale: e' l'unico controllo")
    print("che conta davvero.")


if __name__ == "__main__":
    main()
