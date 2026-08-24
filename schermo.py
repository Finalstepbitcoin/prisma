"""
schermo.py  --  Final Step Bitcoin / Sintesi

Driver dello schermo Waveshare Pico-LCD-1.3 (240x240, chip ST7789)
e lettura del joystick e dei quattro pulsanti.

Gira solo sul dispositivo (MicroPython), non sul Mac.

COLLEGAMENTI (fissi, decisi dal circuito del display):
    schermo   DC=GP8  CS=GP9  CLK=GP10  DIN=GP11  RST=GP12  luce=GP13
    joystick  su=GP2  giu=GP18  sinistra=GP16  destra=GP20  centro=GP3
    pulsanti  A=GP15  B=GP17  X=GP19  Y=GP21

I pulsanti sono "attivi bassi": a riposo leggono 1, premuti leggono 0.

NOTA IMPORTANTE SUL FUNZIONAMENTO (imparata sbagliando):
Il segnale CS dice al pannello "sto parlando con te". Deve restare BASSO
per tutta la durata di un comando E dei suoi dati. Se lo si rialza in mezzo,
il pannello considera il comando annullato e butta via i dati che seguono.
Il risultato e' uno schermo pieno di rumore casuale: si accende (perche' i
comandi senza parametri passano lo stesso) ma non riceve mai i pixel.
Per questo qui c'e' UN SOLO metodo _comando(), che manda comando e dati
insieme senza mai rilasciare CS.
"""

import framebuf
import gc
import time
from machine import SPI, Pin

LARGHEZZA = 240
ALTEZZA = 240


def colore(r, g, b):
    """
    Converte rosso/verde/blu (0-255) nel formato dello schermo.

    Nota tecnica: lo schermo vuole i due byte in ordine inverso rispetto a
    come MicroPython li mette in memoria, quindi li scambiamo qui una volta
    per tutte invece di farlo per ogni pixel.
    """
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return ((c & 0xFF) << 8) | (c >> 8)


NERO = colore(0, 0, 0)
BIANCO = colore(255, 255, 255)
ROSSO = colore(255, 0, 0)
VERDE = colore(0, 255, 0)
BLU = colore(0, 0, 255)
GIALLO = colore(255, 200, 0)
ARANCIO = colore(247, 147, 26)      # arancione Bitcoin
GRIGIO = colore(120, 120, 120)


class Schermo(framebuf.FrameBuffer):
    """
    Lo schermo si disegna in memoria e poi si manda tutto insieme con
    mostra(). Cosi' non si vedono i disegni a meta'.
    """

    def __init__(self, rotazione=0x70, velocita=30_000_000):
        # IL FOGLIO DI DISEGNO VA PRESO PER PRIMO.
        # Servono 115.200 byte TUTTI DI SEGUITO. Dopo aver caricato qualche
        # modulo la memoria e' a chiazze e un blocco cosi' grande non si
        # trova piu', anche se lo spazio totale libero e' abbondante.
        # Sintomo: "MemoryError: memory allocation failed" con centinaia di
        # KB ancora liberi.
        gc.collect()
        self.buffer = bytearray(LARGHEZZA * ALTEZZA * 2)

        # ATTENZIONE, RIGA IMPORTANTE (e' costata un pomeriggio intero):
        #
        # Se non gli si dice niente, MicroPython assegna da solo l'ingresso
        # della linea seriale a GP8. Ma GP8 e' il piedino DC, quello che
        # distingue i comandi dai pixel: se lo prende la periferica seriale
        # resta bloccato e il pannello riceve un flusso che non sa
        # interpretare. Lo schermo mostra rumore casuale.
        #
        # SINTOMO RICONOSCIBILE: la retroilluminazione risponde ai comandi
        # (lampeggia) e il pannello reagisce all'azzeramento (diventa nero),
        # ma l'immagine non compare mai.
        #
        # Non basta scrivere miso=None: viene ignorato. Bisogna spostare
        # l'ingresso su un piedino libero. GP28 non e' usato dal display.
        # 30 MHz richiesti danno 24 MHz reali: il divisore del chip
        # ammette solo 12 o 24 MHz. A 24 lo schermo si ridisegna in 45 ms
        # invece di 91, e i comandi rispondono al doppio della velocita'.
        self.spi = SPI(1, baudrate=velocita, polarity=0, phase=0,
                       sck=Pin(10), mosi=Pin(11), miso=Pin(28))
        self.cs = Pin(9, Pin.OUT, value=1)
        self.dc = Pin(8, Pin.OUT, value=0)
        self.rst = Pin(12, Pin.OUT, value=1)
        self.luce = Pin(13, Pin.OUT, value=1)
        super().__init__(self.buffer, LARGHEZZA, ALTEZZA, framebuf.RGB565)
        self._accendi(rotazione)

    # -- dialogo col chip dello schermo ------------------------------------

    def _comando(self, c, dati=None):
        """
        Manda un comando e, se ci sono, i suoi dati.
        CS resta basso dall'inizio alla fine: e' questo che conta.
        """
        self.cs(0)
        self.dc(0)
        self.spi.write(bytes([c]))
        if dati is not None:
            self.dc(1)
            self.spi.write(dati if isinstance(dati, (bytes, bytearray))
                           else bytes([dati]))
        self.cs(1)

    def _accendi(self, rotazione):
        # riavvio fisico del chip
        self.rst(1); time.sleep_ms(5)
        self.rst(0); time.sleep_ms(20)
        self.rst(1); time.sleep_ms(120)

        self._comando(0x36, rotazione)        # orientamento
        self._comando(0x3A, 0x05)             # 16 bit per pixel

        # parametri elettrici del pannello: valori del costruttore
        self._comando(0xB2, bytes([0x0C, 0x0C, 0x00, 0x33, 0x33]))
        self._comando(0xB7, 0x35)
        self._comando(0xBB, 0x19)
        self._comando(0xC0, 0x2C)
        self._comando(0xC2, 0x01)
        self._comando(0xC3, 0x12)
        self._comando(0xC4, 0x20)
        self._comando(0xC6, 0x0F)
        self._comando(0xD0, bytes([0xA4, 0xA1]))
        self._comando(0xE0, bytes([0xD0, 0x04, 0x0D, 0x11, 0x13,
                                   0x2B, 0x3F, 0x54, 0x4C, 0x18,
                                   0x0D, 0x0B, 0x1F, 0x23]))
        self._comando(0xE1, bytes([0xD0, 0x04, 0x0C, 0x11, 0x13,
                                   0x2C, 0x3F, 0x44, 0x51, 0x2F,
                                   0x1F, 0x1F, 0x20, 0x23]))

        self._comando(0x21)                   # colori non invertiti
        self._comando(0x11); time.sleep_ms(120)   # sveglia
        self._comando(0x29)                   # accendi

        self.fill(NERO)
        self.mostra()

    # -- uso normale --------------------------------------------------------

    def mostra(self):
        """Manda allo schermo tutto quello che e' stato disegnato."""
        self._comando(0x2A, bytes([0x00, 0x00, 0x00, 0xEF]))   # colonne 0-239
        self._comando(0x2B, bytes([0x00, 0x00, 0x00, 0xEF]))   # righe 0-239
        self._comando(0x2C, self.buffer)                       # scrivi i pixel

    def pulisci(self, c=NERO):
        self.fill(c)

    def scritta(self, testo, x, y, c=BIANCO, scala=1):
        """
        Scrive del testo. Con scala=2 o 3 le lettere diventano piu' grandi
        (il carattere di serie e' 8x8 pixel, molto piccolo).
        """
        # Testo vuoto: non c'e' niente da disegnare. Senza questo controllo
        # piu' sotto si proverebbe a creare un'immagine larga ZERO pixel,
        # che manda tutto in errore. Le righe vuote si usano spesso come
        # spaziatura, quindi il caso capita davvero.
        if not testo:
            return
        if scala == 1:
            self.text(testo, x, y, c)
            return
        # per ingrandire disegno prima in piccolo su un foglio a parte,
        # poi copio ogni pixel come un quadratino
        w = len(testo) * 8
        tmp = bytearray(w * 8 * 2)
        fb = framebuf.FrameBuffer(tmp, w, 8, framebuf.RGB565)
        fb.fill(0)
        fb.text(testo, 0, 0, 0xFFFF)
        for ry in range(8):
            for rx in range(w):
                if fb.pixel(rx, ry):
                    self.fill_rect(x + rx * scala, y + ry * scala, scala, scala, c)

    def luminosita(self, accesa=True):
        self.luce(1 if accesa else 0)


class Comandi:
    """Joystick e pulsanti. A riposo leggono 1, premuti 0."""

    NOMI = ("su", "giu", "sinistra", "destra", "centro", "A", "B", "X", "Y")

    def __init__(self):
        self.pin = {
            "su": Pin(2, Pin.IN, Pin.PULL_UP),
            "giu": Pin(18, Pin.IN, Pin.PULL_UP),
            "sinistra": Pin(16, Pin.IN, Pin.PULL_UP),
            "destra": Pin(20, Pin.IN, Pin.PULL_UP),
            "centro": Pin(3, Pin.IN, Pin.PULL_UP),
            "A": Pin(15, Pin.IN, Pin.PULL_UP),
            "B": Pin(17, Pin.IN, Pin.PULL_UP),
            "X": Pin(19, Pin.IN, Pin.PULL_UP),
            "Y": Pin(21, Pin.IN, Pin.PULL_UP),
        }

    def premuti(self):
        """Elenco dei comandi premuti in questo istante."""
        return [n for n in self.NOMI if self.pin[n].value() == 0]

    def attendi(self, scadenza_ms=None):
        """
        Aspetta una pressione e restituisce il nome del comando.
        Gestisce il rimbalzo del contatto e aspetta il rilascio, cosi' una
        pressione vale una volta sola.
        """
        inizio = time.ticks_ms()
        while True:
            for n in self.NOMI:
                if self.pin[n].value() == 0:
                    time.sleep_ms(12)
                    if self.pin[n].value() != 0:
                        continue
                    while self.pin[n].value() == 0:
                        time.sleep_ms(6)
                    time.sleep_ms(12)
                    return n
            if scadenza_ms and time.ticks_diff(time.ticks_ms(), inizio) > scadenza_ms:
                return None
            time.sleep_ms(10)
