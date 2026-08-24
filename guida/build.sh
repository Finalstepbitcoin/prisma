#!/bin/bash
# Genera il PDF della guida d'uso di Sintesi.
# I due logo del canale e il codice QR sono gia' dentro sorgente.html
# come immagini incorporate: non servono file esterni.

set -e
CARTELLA="$(cd "$(dirname "$0")" && pwd)"
SORGENTE="$CARTELLA/sorgente.html"
USCITA="/Users/plak/Desktop/SITO WEB/FILE DA INSERIRE NEL SITO/SINTESI - GUIDA PRATICA.pdf"
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

"$BRAVE" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$USCITA" "file://$SORGENTE" 2>/dev/null

PAGINE=$(/usr/bin/python3 -c "
import re,sys
d=open(sys.argv[1],'rb').read()
print(len(re.findall(rb'/Type\s*/Page[^s]', d)))" "$USCITA")

echo "PDF creato: $USCITA"
echo "Pagine: $PAGINE"
if [ "$PAGINE" != "2" ]; then
  echo "ATTENZIONE: la guida deve stare in DUE pagine (un foglio fronte/retro)."
  echo "Se sono 3: riduci il corpo del testo in sorgente.html (body { font-size })"
  echo "oppure accorcia una delle sezioni."
fi
