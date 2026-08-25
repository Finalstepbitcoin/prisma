"""
impronta.py  --  Final Step Bitcoin / Sintesi

L'impronta del firmware, mostrata all'accensione come tre parole BIP39.

A COSA SERVE
Confrontare le tre parole con quelle pubblicate sul sito e stampate sul
foglietto nella scatola. Se coincidono, il contenuto del dispositivo
corrisponde a quello atteso.

A COSA *NON* SERVE, E VA DETTO CHIARO
Non e' una prova contro manomissioni volute. Un firmware malevolo
mostrerebbe semplicemente le tre parole giuste: il programma che si
controlla da solo e' contemporaneamente l'imputato e il perito. Questo vale
allo stesso modo per chi ha costruito il dispositivo E per chi lo avesse
manomesso dopo (corriere, magazzino, rivenditore): in entrambi i casi
l'attaccante controlla lo stesso codice che calcola questo valore.
Questa impronta vale SOLO contro il deterioramento accidentale della
memoria, non contro una manomissione deliberata di nessun tipo.
La verifica vera si fa da spenti: con picotool, che legge dal bootloader in
ROM e non dal firmware, oppure riflashando tu stesso il .uf2 ufficiale.
Entrambe sono descritte nella guida.

COSA VIENE MISURATO
  1. mezzo megabyte di memoria flash a partire dall'inizio: e' li' che sta
     MicroPython, il resto della zona e' vuoto e quindi sempre uguale
  2. TUTTI i file presenti nel dispositivo, in ordine, percorso compreso -
     non solo i .py, e non solo quelli della cartella principale

Le due cose insieme coprono tutto quello che il dispositivo esegue.
Lo stesso valore si ricalcola sul computer con prepara_impronta.py.
"""

import hashlib
import os

import bip39_checksum as bip39

INIZIO_FLASH = 0x10000000
# ATTENZIONE, LIMITE SCELTO CON CURA (e' costato una caccia all'errore):
# a 0x7F000, cioe' a 508 KB dall'inizio, il Raspberry Pi scrive in fabbrica
# l'esito del proprio collaudo: data, ora e numero di serie della scheda.
# Sono DIVERSI SU OGNI ESEMPLARE. Se finissero nell'impronta, ogni
# dispositivo mostrerebbe tre parole diverse e nessun valore pubblicato
# potrebbe mai corrispondere. Ci fermiamo a 448 KB: sopra il firmware di
# MicroPython (circa 320 KB), sotto i dati di fabbrica.
ZONA_FIRMWARE = 448 * 1024
PAROLE = 3                      # 3 x 11 bit = 33 bit di impronta


def _e_cartella(percorso):
    """Vero se il percorso e' una cartella e non un file."""
    try:
        return os.stat(percorso)[0] & 0x4000 != 0
    except OSError:
        return False


def _aggiungi_file(h, cartella="/"):
    """
    TUTTI i file, in ordine, percorso compreso. Anche quelli dentro le
    sottocartelle, e anche quelli che non finiscono per .py.

    PERCHE' TUTTI E NON SOLO I .py (e' il motivo per cui questa funzione
    esiste in questa forma):
    MicroPython non esegue soltanto i file .py. Sa caricare anche i .mpy,
    cioe' moduli gia' compilati, e cerca i moduli anche nella cartella
    /lib. Misurando i soli .py della cartella principale, un file aggiunto
    con un'altra estensione, o nascosto in una sottocartella, non avrebbe
    cambiato le tre parole - mentre la guida promette il contrario, cioe'
    che basta aggiungere un file perche' cambino.

    Il nome misurato e' il percorso senza la barra iniziale: "main.py",
    oppure "lib/qualcosa.mpy". Su un dispositivo pulito, dove ci sono solo
    i file del programma nella cartella principale, il valore e' identico
    a quello che si otterrebbe misurando i soli nomi: la copertura si
    allarga, il numero non cambia.
    """
    for nome in sorted(os.listdir(cartella)):
        percorso = cartella + nome if cartella.endswith("/") \
            else cartella + "/" + nome
        if _e_cartella(percorso):
            _aggiungi_file(h, percorso)
            continue
        h.update(percorso[1:].encode())     # senza la barra iniziale
        with open(percorso, "rb") as f:
            while True:
                pezzo = f.read(1024)
                if not pezzo:
                    break
                h.update(pezzo)


def calcola():
    """L'impronta completa, in byte."""
    h = hashlib.sha256()
    try:
        import uctypes
        h.update(uctypes.bytearray_at(INIZIO_FLASH, ZONA_FIRMWARE))
    except Exception:
        # se la lettura diretta non fosse possibile, l'impronta copre
        # comunque i file del programma: meglio parziale che assente
        h.update(b"senza-flash")
    _aggiungi_file(h)
    return h.digest()


def parole(digest=None):
    """
    L'impronta come tre parole del dizionario BIP39.

    Tre parole invece di sessantaquattro caratteri esadecimali: si
    confrontano in due secondi anche da chi non e' pratico, ed e' proprio
    il confronto che deve essere facile, altrimenti non lo fa nessuno.
    """
    d = digest or calcola()
    valore = 0
    for b in d[:5]:                 # 40 bit, ne servono 33
        valore = (valore << 8) | b
    valore >>= (40 - 11 * PAROLE)
    fuori = []
    for i in range(PAROLE):
        indice = (valore >> (11 * (PAROLE - 1 - i))) & 0x7FF
        fuori.append(bip39.parola(indice))
    return fuori
