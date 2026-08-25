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
sono l'impronta del firmware caricato sui dispositivi assemblati. Un
Sintesi già montato deve mostrare esattamente quelle all'accensione.

**Se il firmware lo compili tu**, quelle tre parole non ti dicono niente sul
tuo dispositivo: calcola le tue con `python3 prepara_impronta.py` e confronta
con quelle che vedi sullo schermo. È il confronto che conta, non il valore
stampato qui.

A ogni cambio di firmware vengono aggiornate tutte e due le copie della
guida — quella di carta nella scatola e questo PDF — così le tre parole
restano quelle vere.
