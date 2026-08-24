"""
main.py  --  Final Step Bitcoin / Sintesi

MicroPython esegue questo file DA SOLO a ogni accensione.

E' l'unico motivo per cui il dispositivo funziona collegandolo a un
caricatore, senza nessun computer e senza nessun programma.

Non c'e' altro qui dentro di proposito: tutto il resto sta nei moduli, e
questo file deve restare abbastanza corto da poter essere letto e capito
in dieci secondi da chiunque apra il dispositivo per controllarlo.

Per fermarlo e tornare al terminale (serve solo durante lo sviluppo):
CTRL-C sulla porta seriale.
"""

import interfaccia

interfaccia.avvia()
