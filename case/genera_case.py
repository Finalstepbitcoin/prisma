#!/usr/bin/env python3
"""
genera_case.py  --  Final Step Bitcoin / Checksum Tool

Genera i file STL della custodia da stampare in 3D.

GIRA SUL MAC. Non serve installare niente: usa solo Python.
Non serve nemmeno un programma di modellazione: la custodia e' fatta di soli
parallelepipedi, quindi lo si puo' scrivere direttamente.

    python3 genera_case.py

Produce tre file:
    prova_incastro.stl   cornice bassa, 10 minuti di stampa: SERVE A PROVARE
                         se il dispositivo entra, PRIMA di stampare il resto
    vassoio.stl          la scocca inferiore, quella che tiene tutto
    cornice.stl          l'anello superiore che blocca il display

IL COLORE NON STA NEL FILE. Un STL contiene solo la forma: l'arancione lo
dai col filamento. Per avvicinarti all'arancione Bitcoin (#F7931A) cerca un
PLA "arancione" o "orange"; molte marche lo chiamano proprio cosi'.

=============================================================================
LE QUOTE. Quelle marcate DA VERIFICARE vanno misurate sul dispositivo vero
con un righello prima di stampare il case intero: se sbagliano, il pezzo non
entra e hai buttato ore di stampa. La prova d'incastro serve esattamente a
questo.
=============================================================================
"""

import struct
import sys

# --- il dispositivo -------------------------------------------------------

# Raspberry Pi Pico 2: quote dalla scheda tecnica ufficiale
PICO_LUNGHEZZA = 51.0
PICO_LARGHEZZA = 21.0

# Waveshare Pico-LCD-1.3: ingombro dichiarato dal costruttore.
# E' la scheda PIU' LARGA delle due, quindi comanda lei.
SCHEDA_LUNGHEZZA = 52.0
SCHEDA_LARGHEZZA = 26.5

# DA VERIFICARE: altezza di tutto il pacco montato, dal fondo del Pico alla
# superficie del vetro del display. Misurala di taglio con un righello.
ALTEZZA_PACCO = 15.0

# DA VERIFICARE: il connettore micro-USB sporge dal bordo corto del Pico.
# L'apertura e' volutamente PIU' GRANDE del connettore: un buco largo non
# da' nessun fastidio, uno stretto impedisce di infilare il cavo e rende il
# pezzo inutilizzabile. Qui si sbaglia sempre per eccesso.
USB_LARGHEZZA = 11.0       # apertura, non il connettore (che e' circa 8)
USB_ALTEZZA = 5.5          # altezza dell'apertura
USB_DAL_FONDO = 0.6        # a che altezza comincia

# --- la custodia ----------------------------------------------------------

GIOCO = 0.4                # aria fra scheda e parete: meno di 0.3 non entra
PARETE = 2.0               # spessore delle pareti
FONDO = 1.6                # spessore del fondo
BORDO_APPOGGIO = 1.5       # quanto il fondo rientra a fare da appoggio
CORNICE_LARGHEZZA = 2.0    # quanto l'anello superiore copre il bordo scheda
CORNICE_ALTEZZA = 2.0

ALTEZZA_PROVA = 3.0        # la cornice di prova: bassa apposta, si stampa subito


# =========================================================================
# scrittura degli STL: la custodia e' fatta di soli parallelepipedi, quindi
# bastano dodici triangoli per ognuno
# =========================================================================

def triangoli_di_scatola(x, y, z, dx, dy, dz):
    a = (x, y, z)
    b = (x + dx, y, z)
    c = (x + dx, y + dy, z)
    d = (x, y + dy, z)
    e = (x, y, z + dz)
    f = (x + dx, y, z + dz)
    g = (x + dx, y + dy, z + dz)
    h = (x, y + dy, z + dz)
    return [
        (a, c, b), (a, d, c),        # sotto
        (e, f, g), (e, g, h),        # sopra
        (a, b, f), (a, f, e),        # davanti
        (b, c, g), (b, g, f),        # destra
        (c, d, h), (c, h, g),        # dietro
        (d, a, e), (d, e, h),        # sinistra
    ]


def scrivi_stl(nome, scatole):
    triangoli = []
    for s in scatole:
        if s[3] <= 0 or s[4] <= 0 or s[5] <= 0:
            continue
        triangoli += triangoli_di_scatola(*s)
    with open(nome, "wb") as f:
        f.write(b"Final Step Bitcoin - Checksum Tool".ljust(80, b" "))
        f.write(struct.pack("<I", len(triangoli)))
        for t in triangoli:
            f.write(struct.pack("<3f", 0.0, 0.0, 0.0))     # normale: la calcola il programma di stampa
            for punto in t:
                f.write(struct.pack("<3f", *punto))
            f.write(struct.pack("<H", 0))
    return len(triangoli)


# =========================================================================
# 3MF: un file solo con tutti i pezzi, COL COLORE DENTRO
#
# E' il formato che i servizi di stampa preferiscono. A differenza dello STL
# tiene piu' oggetti distinti nello stesso file e porta con se' il colore,
# quindi l'arancione e' dichiarato nel file e non affidato a una nota a
# parte. Un 3MF e' semplicemente un archivio ZIP con dentro dell'XML:
# si scrive con la sola libreria standard di Python.
# =========================================================================

ARANCIO_BITCOIN = "#F7931A"

TIPI = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""

RELAZIONI = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""


def _maglia(scatole):
    """Da parallelepipedi a punti e triangoli, senza ripetere i punti."""
    punti = []
    indice = {}
    facce = []
    for s in scatole:
        if s[3] <= 0 or s[4] <= 0 or s[5] <= 0:
            continue
        for t in triangoli_di_scatola(*s):
            f = []
            for p in t:
                chiave = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
                if chiave not in indice:
                    indice[chiave] = len(punti)
                    punti.append(chiave)
                f.append(indice[chiave])
            facce.append(f)
    return punti, facce


def scrivi_3mf(nome, oggetti):
    """oggetti: elenco di (nome, scatole, spostamento_y)."""
    import zipfile

    righe = ['<?xml version="1.0" encoding="UTF-8"?>']
    righe.append('<model unit="millimeter" xml:lang="it-IT"'
                 ' xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"'
                 ' xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">')
    righe.append(' <metadata name="Title">Checksum Tool - custodia</metadata>')
    righe.append(' <metadata name="Designer">Final Step Bitcoin</metadata>')
    righe.append(' <resources>')
    righe.append('  <m:colorgroup id="1"><m:color color="%s"/></m:colorgroup>'
                 % ARANCIO_BITCOIN)

    costruzione = []
    ident = 2
    for etichetta, scatole, spostamento in oggetti:
        punti, facce = _maglia(scatole)
        righe.append('  <object id="%d" name="%s" type="model" pid="1" pindex="0">'
                     % (ident, etichetta))
        righe.append('   <mesh>')
        righe.append('    <vertices>')
        for p in punti:
            righe.append('     <vertex x="%.4f" y="%.4f" z="%.4f"/>' % p)
        righe.append('    </vertices>')
        righe.append('    <triangles>')
        for f in facce:
            righe.append('     <triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f))
        righe.append('    </triangles>')
        righe.append('   </mesh>')
        righe.append('  </object>')
        costruzione.append('  <item objectid="%d" transform="1 0 0 0 1 0 0 0 1 0 %.1f 0"/>'
                           % (ident, spostamento))
        ident += 1

    righe.append(' </resources>')
    righe.append(' <build>')
    righe += costruzione
    righe.append(' </build>')
    righe.append('</model>')
    modello = "\n".join(righe)

    with zipfile.ZipFile(nome, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", TIPI)
        z.writestr("_rels/.rels", RELAZIONI)
        z.writestr("3D/3dmodel.model", modello)
    return sum(len(_maglia(s)[1]) for _, s, _ in oggetti)


# =========================================================================
# i pezzi
# =========================================================================

def misure_cavita():
    """Il vano interno dove va il dispositivo."""
    return (SCHEDA_LUNGHEZZA + 2 * GIOCO, SCHEDA_LARGHEZZA + 2 * GIOCO)


def pareti(altezza, con_fondo, z0=0.0):
    """
    Le quattro pareti (piu' il fondo se richiesto) come parallelepipedi.
    Il buco per il micro-USB si ottiene NON mettendo materiale: la parete
    corta viene spezzata in tre pezzi, due laterali e uno sopra il buco.
    """
    cl, cw = misure_cavita()
    el = cl + 2 * PARETE          # ingombro esterno
    ew = cw + 2 * PARETE
    pezzi = []

    if con_fondo:
        pezzi.append((0, 0, 0, el, ew, FONDO))
        z0 = FONDO

    h = altezza

    # parete lunga davanti e dietro
    pezzi.append((0, 0, z0, el, PARETE, h))
    pezzi.append((0, ew - PARETE, z0, el, PARETE, h))

    # parete corta senza buco (lato opposto all'USB)
    pezzi.append((el - PARETE, PARETE, z0, PARETE, cw, h))

    # parete corta col buco per il micro-USB, spezzata in tre
    lato = (cw - USB_LARGHEZZA) / 2.0
    pezzi.append((0, PARETE, z0, PARETE, lato, h))
    pezzi.append((0, ew - PARETE - lato, z0, PARETE, lato, h))
    sopra_buco = z0 + USB_DAL_FONDO + USB_ALTEZZA
    resto = (z0 + h) - sopra_buco
    if resto > 0:
        pezzi.append((0, PARETE + lato, sopra_buco, PARETE, USB_LARGHEZZA, resto))
    if USB_DAL_FONDO > 0:
        pezzi.append((0, PARETE + lato, z0, PARETE, USB_LARGHEZZA, USB_DAL_FONDO))

    return pezzi, el, ew


def vassoio():
    """
    La scocca inferiore. Dentro, un gradino tutt'intorno tiene il dispositivo
    sollevato dal fondo: serve a non appoggiare le saldature.
    """
    cl, cw = misure_cavita()
    pezzi, el, ew = pareti(ALTEZZA_PACCO, con_fondo=True)

    # Gradino d'appoggio: un anello sottile lungo il perimetro interno.
    # I quattro pezzi si TOCCANO senza sovrapporsi: i due corti partono
    # dopo quelli lunghi. Le sovrapposizioni creano pareti interne che i
    # controlli automatici dei servizi di stampa segnalano come difetti.
    z = FONDO
    a = BORDO_APPOGGIO
    pezzi.append((PARETE, PARETE, z, cl, a, 1.0))
    pezzi.append((PARETE, ew - PARETE - a, z, cl, a, 1.0))
    pezzi.append((PARETE, PARETE + a, z, a, cw - 2 * a, 1.0))
    pezzi.append((el - PARETE - a, PARETE + a, z, a, cw - 2 * a, 1.0))
    return pezzi, el, ew


def cornice():
    """
    L'anello che va sopra e blocca il display.

    Copre SOLO i due lati lunghi: i lati corti restano liberi perche' li'
    ci sono il joystick e i quattro pulsanti, e coprirli anche di poco li
    renderebbe scomodi da premere.
    """
    cl, cw = misure_cavita()
    el = cl + 2 * PARETE
    ew = cw + 2 * PARETE
    c = CORNICE_LARGHEZZA
    pezzi = [
        (0, 0, 0, el, PARETE + c, CORNICE_ALTEZZA),
        (0, ew - PARETE - c, 0, el, PARETE + c, CORNICE_ALTEZZA),
    ]
    return pezzi, el, ew


def main():
    cl, cw = misure_cavita()
    print("=" * 62)
    print("  CUSTODIA - Checksum Tool")
    print("=" * 62)
    print("\nvano interno   %.1f x %.1f mm  (scheda %.1f x %.1f + %.1f di gioco)"
          % (cl, cw, SCHEDA_LUNGHEZZA, SCHEDA_LARGHEZZA, GIOCO))

    pezzi, el, ew = vassoio()
    n = scrivi_stl("vassoio.stl", pezzi)
    print("\nvassoio.stl          %.1f x %.1f x %.1f mm   (%d triangoli)"
          % (el, ew, FONDO + ALTEZZA_PACCO, n))

    pezzi, el, ew = cornice()
    n = scrivi_stl("cornice.stl", pezzi)
    print("cornice.stl          %.1f x %.1f x %.1f mm   (%d triangoli)"
          % (el, ew, CORNICE_ALTEZZA, n))

    pezzi, el, ew = pareti(ALTEZZA_PROVA, con_fondo=False)
    n = scrivi_stl("prova_incastro.stl", pezzi)
    print("prova_incastro.stl   %.1f x %.1f x %.1f mm   (%d triangoli)"
          % (el, ew, ALTEZZA_PROVA, n))

    # il file unico da mandare a un servizio di stampa
    pezzi_v, _, ew = vassoio()
    pezzi_c, _, _ = cornice()
    n = scrivi_3mf("custodia_completa.3mf",
                   [("vassoio", pezzi_v, 0.0),
                    ("cornice", pezzi_c, ew + 5.0)])
    print("custodia_completa.3mf  ENTRAMBI i pezzi + colore %s   (%d triangoli)"
          % (ARANCIO_BITCOIN, n))

    # stesso contenuto in STL, per i servizi che accettano solo quel formato.
    # I due pezzi vengono affiancati come nel 3MF.
    affiancati = list(pezzi_v)
    for s in pezzi_c:
        affiancati.append((s[0], s[1] + ew + 5.0, s[2], s[3], s[4], s[5]))
    n = scrivi_stl("custodia_completa.stl", affiancati)
    print("custodia_completa.stl  ENTRAMBI i pezzi, senza colore   (%d triangoli)" % n)

    print("\n" + "-" * 62)
    print("  STAMPA PRIMA prova_incastro.stl: dieci minuti, e ti dice")
    print("  se il dispositivo entra. Se e' stretto alza GIOCO di 0.2 e")
    print("  rigenera; se balla, abbassalo.")
    print("-" * 62)
    print("\n  DA MISURARE SUL DISPOSITIVO PRIMA DI STAMPARE IL RESTO:")
    print("   - altezza del pacco montato, di taglio ........ ora %.1f mm"
          % ALTEZZA_PACCO)
    print("   - larghezza del connettore micro-USB .......... ora %.1f mm"
          % USB_LARGHEZZA)
    print("   - altezza del connettore dal fondo ............ ora %.1f mm"
          % USB_DAL_FONDO)
    print("\n  Filamento: PLA arancione. L'arancione Bitcoin e' #F7931A.")


if __name__ == "__main__":
    main()
