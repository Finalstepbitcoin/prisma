#!/bin/bash
# Genera il PDF della guida d'uso di Prisma.
# I due logo del canale e il codice QR sono gia' dentro sorgente.html
# come immagini incorporate: non servono file esterni.

set -e
CARTELLA="$(cd "$(dirname "$0")" && pwd)"
PROGETTO="$(dirname "$CARTELLA")"
SORGENTE="$CARTELLA/sorgente.html"
# Il PDF nasce dentro il repository: e' l'unico posto che esiste su
# qualunque computer. Chi lo stampa spesso puo' volerne una copia anche
# altrove (una cartella da caricare sul sito, per dire): basta scrivere quel
# percorso dentro guida/copia-locale.txt, che resta fuori dal repository.
USCITA="$CARTELLA/PRISMA - GUIDA PRATICA.pdf"
COPIA_LOCALE=""
if [ -f "$CARTELLA/copia-locale.txt" ]; then
  COPIA_LOCALE="$(head -1 "$CARTELLA/copia-locale.txt")"
fi
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

# ---------------------------------------------------------------------------
# CONTROLLO DELLE TRE PAROLE DELL'IMPRONTA — si fa PRIMA di stampare.
#
# Sul foglio sono stampate le tre parole che il dispositivo deve mostrare
# all'accensione. Se cambia anche un solo file del firmware, quelle parole
# cambiano: una guida vecchia farebbe sembrare MANOMESSO un dispositivo
# sano, ed e' il danno peggiore possibile, perche' insegna a chi compra a
# ignorare la differenza. Quindi qui ci si ferma, invece di stampare.
# ---------------------------------------------------------------------------
ATTESE=$(cd "$PROGETTO" && /usr/bin/python3 prepara_impronta.py --parole 2>/dev/null || true)
if [ -z "$ATTESE" ]; then
  echo "ERRORE: non riesco a calcolare l'impronta del firmware."
  echo "Serve il .uf2 di MicroPython in firmware/ e i file generati"
  echo "(wordlist.py, diceware_*.py, qr_canale.py). Lancia a mano:"
  echo "    cd \"$PROGETTO\" && python3 prepara_impronta.py"
  echo "e guarda cosa si lamenta. Il PDF non e' stato toccato."
  exit 1
fi

STAMPATE=$(/usr/bin/python3 -c "
import re, sys
testo = open(sys.argv[1], encoding='utf-8').read()
trovato = re.search(r'<div class=\"parole\">(.*?)</div>', testo)
if not trovato:
    sys.exit('NESSUNA')
riga = trovato.group(1).replace('&nbsp;', ' ')
print(' '.join(riga.split()).upper())" "$SORGENTE")

if [ "$ATTESE" != "$STAMPATE" ]; then
  echo "ERRORE: le tre parole sul foglio non sono quelle del firmware."
  echo "  sul foglio (sorgente.html) : $STAMPATE"
  echo "  firmware di adesso         : $ATTESE"
  echo
  echo "Correggi la riga <div class=\"parole\"> dentro sorgente.html mettendo"
  echo "le parole del firmware, poi rilancia. Il PDF non e' stato toccato."
  exit 1
fi
echo "Impronta: $ATTESE — il foglio e il firmware dicono la stessa cosa."

"$BRAVE" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$USCITA" "file://$SORGENTE" 2>/dev/null

PAGINE=$(/usr/bin/python3 -c "
import re,sys
d=open(sys.argv[1],'rb').read()
print(len(re.findall(rb'/Type\s*/Page[^s]', d)))" "$USCITA")

# La copia in piu' si fa in automatico, non a mano: se restasse da fare a
# mano, prima o poi si ristampa il foglio e ci si dimentica di aggiornare
# l'altra copia, e chi la usa si ritrova tre parole d'impronta che non sono
# piu' quelle del firmware consegnato.
if [ -n "$COPIA_LOCALE" ] && [ -d "$(dirname "$COPIA_LOCALE")" ]; then
  cp "$USCITA" "$COPIA_LOCALE"
  echo "  copia anche in: $COPIA_LOCALE"
fi

# Sul foglio c'e' scritto di confrontare le tre parole con quelle pubblicate
# su Nostr. Se la nota non c'e', quella riga manda il lettore nel vuoto.
echo
echo "RICORDA: sul foglio c'e' scritto di confrontare le tre parole con"
echo "quelle pubblicate su Nostr. Prima di stampare, pubblica la nota con"
echo "  $ATTESE"
echo "Il testo gia' pronto lo stampa crea_uf2.py."
echo
echo "PDF creato: guida/PRISMA - GUIDA PRATICA.pdf"
echo "Pagine: $PAGINE"
if [ "$PAGINE" != "2" ]; then
  echo "ATTENZIONE: la guida deve stare in DUE pagine (un foglio fronte/retro)."
  echo "Se sono 3: riduci il corpo del testo in sorgente.html (body { font-size })"
  echo "oppure accorcia una delle sezioni."
fi
