# Sintesi — Final Step Bitcoin

Un piccolo dispositivo **offline** che fa due cose sole:

1. **completa un seed BIP39** — gli dai le prime 11 (o 23) parole, lui calcola l'ultima
2. **genera una passphrase col metodo Diceware** — tu tiri i dadi, lui traduce i numeri in parole

Costa circa **20 euro** di componenti (aggiornato al 19 agosto 2026, a cui va aggiunto il case), non ha WiFi né Bluetooth, non salva niente
e il firmware è ispezionabile e riscrivibile da chiunque.

Canale YouTube: [Final Step Bitcoin](https://www.youtube.com/@final_step_bitcoin)

---

## Cosa serve

| Pezzo | Codice | Prezzo |
|---|---|---|
| Raspberry Pi Pico 2 con header | `RPI-PICO2-H` | ~7 € |
| Waveshare Pico-LCD-1.3 (240×240, joystick + 4 tasti) | `WS-19650` | ~9 € |
| Cavo micro-USB **dati** | `RPI-MUSB-1` | ~1,80 € |

**Attenzione a non prendere la versione "W"** del Pico: quella ha WiFi e Bluetooth,
e vanifica tutto il senso del progetto.

I due pezzi si incastrano. Il display va montato allineando il
simbolo USB stampato sul suo circuito con il connettore USB del Pico.

---

## Perché è fatto così

**Nessuna radio a bordo.** L'RP2350 non ha WiFi né Bluetooth: non è una scelta
del firmware, è il silicio che non li ha. È la garanzia più solida possibile.

**Non scrive nulla nella memoria permanente.** Le parole restano solo nella
memoria di lavoro e spariscono togliendo corrente. Questa scelta ha una
conseguenza importante: la memoria del dispositivo è **deterministica**, quindi
si può leggere e confrontare con quella di chiunque altro.

**Non genera entropia, la conserva.** Il caso lo porti tu — coi dadi, con una
moneta, come preferisci. Il dispositivo fa solo la traduzione, la stessa che
faresti a mano con le liste stampate, senza sbagliare riga.

**Non calcola chiavi private.** Niente derivazione, niente PBKDF2: il dispositivo
non può risalire al tuo portafoglio nemmeno per sbaglio.

**Il secure boot è deliberatamente disattivato.** Attivarlo impedirebbe
all'acquirente di riscrivere il firmware, cioè la garanzia più forte che questo
progetto possa offrire. È un pregio, non una mancanza.

---

## Come si costruisce

Serve solo Python 3 sul Mac o sul PC. Nessuna libreria da installare.

```bash
# 1. scarica dizionario e liste dalle fonti ufficiali, e disegna il QR
python3 prepara_wordlist.py
python3 prepara_diceware.py
.venv-strumenti/bin/python prepara_qr.py     # solo se cambia l'indirizzo

# 2. verifica che i calcoli siano corretti, PRIMA di toccare il dispositivo
python3 test_bip39.py
python3 test_diceware.py

# 3. carica MicroPython sul Pico: tieni premuto BOOTSEL mentre colleghi il
#    cavo, poi trascina il file .uf2 sul disco RP2350 che compare

# 4. copia tutto sul dispositivo
python3 installa.py

# 5. annota le tre parole da pubblicare e stampare
python3 prepara_impronta.py
```

**Le liste di parole non stanno in questo repository**: si scaricano dalle
fonti originali al momento della compilazione, e ognuna resta sotto la propria
licenza. Gli script verificano che siano complete e ne stampano l'impronta
SHA-256.

---

## I file

**Girano sul dispositivo**

| File | Cosa fa |
|---|---|
| `main.py` | tre righe: fa partire tutto all'accensione |
| `interfaccia.py` | menu, inserimento delle parole, schermate |
| `bip39_checksum.py` | il calcolo del checksum BIP39 |
| `diceware.py` | dai numeri dei dadi alle parole |
| `schermo.py` | driver del display e lettura dei comandi |

**Girano sul computer**

| File | Cosa fa |
|---|---|
| `prepara_wordlist.py` | scarica e verifica il dizionario BIP39 |
| `prepara_diceware.py` | scarica e verifica le due liste Diceware |
| `test_bip39.py` | confronta i calcoli coi vettori ufficiali BIP39 |
| `test_diceware.py` | riconfronta le liste con le fonti, voce per voce |
| `prepara_qr.py` | disegna il QR del canale (unico script con una dipendenza) |
| `prepara_impronta.py` | calcola l'impronta attesa, da pubblicare e stampare |
| `installa.py` | copia tutti i file sul dispositivo in un colpo solo |
| `parla_col_pico.py` | parla col dispositivo senza installare programmi |
| `prova_percorsi.py` | ripercorre da solo tutte le strade dell'interfaccia |

---

## Come si verifica

I test scaricano i **vettori ufficiali BIP39** e controllano che il motore dia
esattamente i risultati previsti dallo standard — non "sembra funzionare", ma
*è dimostrato conforme*.

```
python3 test_bip39.py      →  186 controlli
python3 test_diceware.py   →   32 controlli
```

E sul dispositivo, una prova che ripercorre da sola ogni schermata e ogni
strada dell'interfaccia — inserimento parole, bit, dadi, ritorni indietro,
avvisi — controllando che nessuna finisca in errore:

```
python3 parla_col_pico.py copia prova_percorsi.py
python3 parla_col_pico.py esegui --pulito "import prova_percorsi"
                           →  18 percorsi
```

**Ricordati di togliere `prova_percorsi.py` dal dispositivo quando hai
finito**: e' un file in piu', quindi cambia l'impronta.

Fra questi ci sono due verifiche che vale la pena citare:

- la versione veloce del calcolo viene confrontata con una versione lenta e
  ovvia, tenuta nel codice apposta come metro di paragone
- per **tutte e 128** le posizioni possibili si verifica che i bit di entropia
  forniti dall'utente finiscano nella parola giusta

## L'impronta del firmware

All'accensione il dispositivo mostra **tre parole BIP39**. Sono i primi 33 bit
dello SHA-256 di tutto quello che esegue: la memoria del firmware piu' il
contenuto di ogni file del programma.

```
python3 prepara_impronta.py
```

calcola lo stesso valore sul computer. Se le tre parole coincidono, dentro il
dispositivo c'e' esattamente quello che c'e' in questo repository.

Basta aggiungere un file perche' cambino: e' proprio quello che devono fare.

**Attenzione a cosa dimostra, e cosa NON dimostra**: e' il firmware stesso a
calcolare e mostrare queste tre parole. Un firmware malevolo mostrerebbe
comunque le parole giuste — sia che la manomissione sia avvenuta durante la
costruzione, sia durante il trasporto, in magazzino o presso un rivenditore:
in tutti questi casi chi manomette il dispositivo controlla lo stesso codice
che calcola l'impronta, e puo' farla tornare giusta a piacere.

Questo controllo serve solo contro il deterioramento accidentale della
memoria (un bit corrotto, un file mancante), **non contro una manomissione
voluta, di nessun tipo**. Per una prova vera serve leggere il contenuto da
SPENTI, con un canale che il firmware non controlla:

- `picotool save -a` / `picotool verify` da BOOTSEL, che risponde il
  bootloader in ROM col firmware fermo — vedi la guida
- oppure riflashare tu stesso il `.uf2` ufficiale, che sostituisce
  qualunque cosa ci fosse prima

---

## Comandi

| | |
|---|---|
| joystick | si muove fra lettere, voci di menu, elenchi |
| A | conferma, scegli |
| B | cancella, torna indietro |
| X e Y | i valori 1 e 0 quando si inseriscono i bit |

Nei tiri di dado: su = 1, destra = 2, giù = 3, sinistra = 4, centro = 5,
tasto X = 6. Lo schema è disegnato sullo schermo.

---

## Avvertenze

**Spegnere significa staccare il cavo, non premere RESET.** Il reset riavvia il
processore ma non azzera la memoria di lavoro.

**Una passphrase non ha checksum.** Se la trascrivi male non te ne accorgi: non
compare nessun errore, entri semplicemente in un altro portafoglio, vuoto. Il
seed BIP39 invece da questo ti protegge.

**Alimentalo da un caricatore da telefono**, non dal computer. Molte power bank
si spengono da sole quando l'assorbimento è basso come quello di questo
dispositivo.

**Questo progetto non è stato sottoposto ad audit professionali.** I calcoli sono
verificati contro i vettori ufficiali, il resto è codice scritto con cura ma non
revisionato da terzi. Trattalo di conseguenza.

---

## Licenze

Il codice di questo progetto è sotto licenza **MIT** (vedi `LICENSE`).

Le liste di parole non sono incluse qui e restano di chi le ha fatte. Il
firmware assemblato, contenendo la lista Diceware italiana, esce sotto
**GPL-3.0**. I dettagli sono in [`LICENZE-TERZI.md`](LICENZE-TERZI.md).
