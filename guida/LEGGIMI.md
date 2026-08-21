# Guida d'uso — "Checksum Tool, guida in un foglio"

Il foglio A4 **fronte/retro** che va nella scatola insieme al dispositivo.
Parla a chi il dispositivo lo compra già pronto: come si accende, come si usano
le due modalità, come si verifica il firmware, cosa non bisogna fare.

Stessa testata, stessi font e stesso piede di pagina delle schede
`scheda-bip39/` e `scheda-diceware/`: le tre carte devono sembrare una collana.

## Come rigenerare il PDF

```
./build.sh
```

Il PDF finisce direttamente in
`~/Desktop/SITO WEB/FILE DA INSERIRE NEL SITO/CHECKSUM TOOL - GUIDA IN UN FOGLIO.pdf`.

Lo script controlla da solo che la guida stia in **due pagine** e avvisa se
sfora.

## VINCOLO: deve stare in due facciate

Un foglio solo, stampato fronte/retro. La prima facciata ha 277 mm di altezza
utile e ne usa circa 275: **non c'è margine**. Se aggiungi tre righe, sfora e
diventano tre pagine.

Se devi far spazio, in ordine di convenienza:

1. accorcia il testo di un passo (ogni riga in meno vale circa 3 mm)
2. `body { font-size }` — ora è a 8.9pt, sotto gli 8.4pt diventa faticoso da
   leggere su carta
3. `h2 { margin }` — ora 2.4mm sopra e 1.5mm sotto

Per **vedere la seconda facciata** (`qlmanage -t` mostra solo la prima, e sul
Mac non ci sono poppler/PIL/ImageMagick): duplica `sorgente.html` aggiungendo
prima di `</head>`

```html
<style>@media print{ body > *:not(.facciata2){display:none}
.facciata2{break-before:auto;page-break-before:auto;padding-top:0} }</style>
```

e stampa quello.

## DA AGGIORNARE A OGNI VERSIONE DEL FIRMWARE

Sulla facciata 1 sono stampate le **tre parole dell'impronta**, dentro il
riquadro arancione:

```html
<div class="parole">BEAN &nbsp;ARRANGE &nbsp;ONE</div>
```

Sono l'impronta della versione **1.0**. Basta cambiare un file del dispositivo
perché diventino altre tre: se ristampi la guida senza ricalcolarle, chi compra
il dispositivo trova tre parole diverse da quelle sullo schermo e pensa a una
manomissione.

Prima di ogni ristampa, quindi:

```
cd ..
python3 prepara_impronta.py
```

e copia qui le tre parole che stampa.

**TRAPPOLA TROVATA (21/8/2026): il riquadro dell'impronta non ha margine
per parole lunghe.** Il font di `.impronta .parole` era a 15pt: con tre
parole BIP39 piu' lunghe della media (es. "BETWEEN INMATE NOODLE" contro
"BEAN ARRANGE ONE") il testo andava a capo dentro il riquadro, la facciata 1
sforava di una riga e la guida passava da 2 a 3 pagine — un sintomo
lontanissimo dalla causa vera, ci ho messo un po' a isolarlo. Portato a
10.5pt: ci stanno comodamente anche le triplette piu' lunghe viste finora.
Se in futuro `build.sh` segnala di nuovo 3 pagine dopo aver solo incollato
tre parole nuove, guarda qui prima che nel testo delle sezioni.

## Il codice QR

Punta a `https://www.finalstepbitcoin.com/checksum`, la pagina dove stanno il
file `.uf2` ufficiale, le istruzioni per riscrivere il firmware e lo strumento
di verifica. **Quella pagina va creata prima di stampare la guida**: un QR che
finisce su un errore 404 è peggio di nessun QR.

Il QR è disegnato dentro `sorgente.html` come SVG, non è un'immagine esterna.
Se l'indirizzo cambia:

```
../.venv-strumenti/bin/python prepara_qr_guida.py
```

poi incolla il contenuto di `qr-verifica.svg.txt` al posto del vecchio
`<svg class="qr">` dentro `sorgente.html`, aggiorna la scritta sotto il QR e
rilancia `build.sh`. **Inquadra sempre col telefono il QR sul PDF finale**: è
l'unico controllo che conta.

Il QR va **stampato**, non mostrato dal dispositivo: un firmware manomesso
mostrerebbe sullo schermo un indirizzo falso, e manderebbe chi verifica su una
pagina scritta da chi l'ha manomesso. La carta non la riscrive nessuno.

## Da dove vengono i due logo

Sono già dentro `sorgente.html` come immagini incorporate (base64), quindi il
file è autosufficiente. Le stesse due immagini stanno in
`../scheda-diceware/sorgente.html`: il lettering `FINAL ⚡TEP ₿ITCOIN`
(`<img class="brandmark">`) e l'icona quadrata del piede di pagina.

## Cosa dice la guida, e perché

Le sette sezioni ricalcano l'ordine in cui uno tira fuori il dispositivo dalla
scatola: cosa fa → accendilo e controlla l'impronta → i comandi → checksum →
passphrase → verifica del firmware → avvertenze.

Tre punti sono lì apposta e non vanno tolti per fare spazio:

- **"Le 128 parole finali non sono una scelta"** — è il concetto che regge tutto
  il dispositivo: i 7 bit che avanzano non sono un dettaglio tecnico, sono
  entropia che si butta via scegliendo la parola "che suona bene".
- **"Una passphrase non ha checksum"** — è l'unico modo in cui un utente può
  perdere dei fondi usando questo dispositivo.
- **Livello 2 prima del livello 3** — riscrivere il firmware da soli è insieme
  la strada più semplice e la più sicura, e va offerta per prima.
