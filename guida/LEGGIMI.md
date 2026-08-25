# Guida d'uso — "Sintesi, guida pratica"

Questa guida spiega l'utilizzo del dispositivo: come si accende, come si usano
le due modalità, come si verifica il firmware, cosa non bisogna fare. Viene
consegnata a chi acquista "Sintesi" già assemblato.

## Il PDF

`SINTESI - GUIDA PRATICA.pdf` è il foglio pronto da stampare, fronte/retro
su un A4. È la stessa identica copia che finisce nella scatola: `build.sh`
la aggiorna qui in automatico ogni volta che rigenera il foglio, così le due
non possono divergere.

### Attenzione alle tre parole stampate sopra

Sulla prima facciata, nel riquadro arancione, ci sono **tre parole BIP39**:
sono l'impronta del firmware che **ho caricato io** sui dispositivi che
vendo assemblati. Se compri Sintesi già montato, all'accensione deve
mostrare esattamente quelle.

**Se il firmware lo compili tu**, quelle tre parole non ti dicono niente sul
tuo dispositivo: calcola le tue con `python3 prepara_impronta.py` e confronta
con quelle che vedi sullo schermo. È il confronto che conta, non il valore
stampato qui.

Quando cambio il firmware aggiorno tutte e due le copie della guida — quella
di carta nella scatola e questo PDF — così le tre parole restano quelle vere.

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

## Cosa dice la guida, e perché

Le sette sezioni ricalcano l'ordine in cui uno tira fuori il dispositivo dalla
scatola: cosa fa → accendilo e controlla l'impronta → i comandi → checksum →
passphrase → verifica del firmware → avvertenze.

Tre punti sono lì apposta e non vanno tolti per fare spazio:

- **"Una passphrase non ha checksum"** — è l'unico modo in cui un utente può
  perdere dei fondi usando questo dispositivo.
- **"Non fotografare lo schermo"**, ripetuto in tutte e due le modalità — è
  l'errore più comune e più grave: la foto finisce nel backup del telefono, e
  il segreto è su un server di qualcun altro.
- **Livello 2 prima del livello 3** — riscrivere il firmware da soli è insieme
  la strada più semplice e la più sicura, e va offerta per prima.

Il blocco *"Le 128 parole finali non sono una scelta"* stava qui fino al
22 agosto 2026 ed è stato tolto per fare spazio. Il concetto — i 7 bit che
avanzano sono entropia, non un dettaglio tecnico — resta comunque nel passo
"Scegli come completare", dove "Tutti zeri" è descritto come buttarli via.
