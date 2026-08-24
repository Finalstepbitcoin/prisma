"""
bip39_checksum.py  --  Final Step Bitcoin / Sintesi

Il motore di calcolo. Gira identico sul Mac (Python 3) e sul dispositivo
(MicroPython sul Raspberry Pi Pico 2).

COSA FA
  - dice se una frase mnemonica e' valida
  - dato un elenco incompleto (11 o 23 parole) trova TUTTE le ultime
    parole valide
  - gestisce l'autocompletamento durante l'inserimento

COSA NON FA, DI PROPOSITO
  - non scrive NIENTE in memoria: nessun file, nessuna impostazione salvata,
    nessuna traccia. Il dispositivo esce dalla fabbrica e resta identico per
    sempre. E' questa scelta che rende verificabile il firmware.
  - non calcola chiavi private (niente PBKDF2, niente derivazione): il
    dispositivo non deve poter risalire al tuo wallet, nemmeno per sbaglio.
  - non usa internet, non ha bisogno di internet.

NOTA SUL PERCHE' PROVIAMO TUTTE E 2048 LE PAROLE
  Si potrebbe calcolare la parola finale direttamente manipolando i bit.
  Ho scelto invece di provarle tutte e tenere quelle che passano la verifica.
  E' altrettanto istantaneo, ma soprattutto: tutta la parte delicata resta
  dentro una sola funzione di controllo, che chiunque puo' leggere e
  verificare contro i vettori ufficiali BIP39. Meno codice furbo = meno bug.
"""

try:
    import hashlib
except ImportError:          # MicroPython su alcune versioni
    import uhashlib as hashlib

from wordlist import BLOB, N_PAROLE, LARGHEZZA

# Lunghezze di frase ammesse dallo standard BIP39
LUNGHEZZE_VALIDE = (12, 15, 18, 21, 24)


# ---------------------------------------------------------------------------
# Dizionario
# ---------------------------------------------------------------------------

def parola(i):
    """Restituisce la parola numero i (da 0 a 2047)."""
    if i < 0 or i >= N_PAROLE:
        raise ValueError("indice fuori range: %d" % i)
    return BLOB[i * LARGHEZZA:(i + 1) * LARGHEZZA].rstrip()


def indice_di(p):
    """
    Numero della parola nel dizionario, oppure None se non esiste.
    Ricerca binaria: il dizionario e' in ordine alfabetico.
    """
    p = p.strip().lower()
    basso, alto = 0, N_PAROLE - 1
    while basso <= alto:
        mezzo = (basso + alto) // 2
        corrente = parola(mezzo)
        if corrente == p:
            return mezzo
        if corrente < p:
            basso = mezzo + 1
        else:
            alto = mezzo - 1
    return None


def _primo_con_prefisso(prefisso):
    """Posizione della prima parola che inizia con 'prefisso' (ricerca binaria)."""
    basso, alto = 0, N_PAROLE
    while basso < alto:
        mezzo = (basso + alto) // 2
        if parola(mezzo) < prefisso:
            basso = mezzo + 1
        else:
            alto = mezzo
    return basso


# ---------------------------------------------------------------------------
# Autocompletamento  (quello che serve all'interfaccia col joystick)
# ---------------------------------------------------------------------------

def completa(prefisso, massimo=None):
    """
    Tutte le parole che iniziano con 'prefisso'.

    Esempi:
        completa("aban")  -> ["abandon"]
        completa("ac")    -> ["access", "accident", ...]
    """
    prefisso = prefisso.strip().lower()
    if prefisso == "":
        return [parola(i) for i in range(N_PAROLE)][:massimo] if massimo else \
               [parola(i) for i in range(N_PAROLE)]
    trovate = []
    i = _primo_con_prefisso(prefisso)
    while i < N_PAROLE:
        p = parola(i)
        if not p.startswith(prefisso):
            break
        trovate.append(p)
        if massimo is not None and len(trovate) >= massimo:
            break
        i += 1
    return trovate


_INIZIALI = None


def lettere_possibili(prefisso):
    """
    Quali lettere hanno senso DOPO il prefisso gia' digitato.

    E' la funzione che rende veloce l'inserimento col joystick: invece di
    scorrere tutte e 26 le lettere, l'utente ne vede solo quelle che portano
    davvero a una parola.

    Esempio: dopo "abo" restano "u" e "v"  (about, above)
    """
    prefisso = prefisso.strip().lower()

    # Caso speciale: prefisso vuoto, cioe' la PRIMA lettera della parola.
    # La risposta e' sempre la stessa (le 25 iniziali del dizionario: nel
    # BIP39 inglese nessuna parola comincia per "x"), ma calcolarla
    # scorrendo tutte e 2048 le parole costa oltre 3 secondi sul
    # dispositivo. La calcoliamo una volta sola e la teniamo da parte,
    # leggendo le iniziali direttamente dal blocco senza costruire le
    # parole intere.
    if not prefisso:
        global _INIZIALI
        if _INIZIALI is None:
            trovate = []
            for i in range(N_PAROLE):
                L = BLOB[i * LARGHEZZA]
                if L not in trovate:
                    trovate.append(L)
            _INIZIALI = trovate
        return list(_INIZIALI)

    n = len(prefisso)
    lettere = []
    i = _primo_con_prefisso(prefisso) if prefisso else 0
    while i < N_PAROLE:
        p = parola(i)
        if prefisso and not p.startswith(prefisso):
            break
        if len(p) > n:
            L = p[n]
            if L not in lettere:
                lettere.append(L)
        i += 1
    return lettere


def parola_unica(prefisso):
    """
    Se il prefisso identifica gia' una sola parola la restituisce, altrimenti None.
    Serve per completare da soli appena non c'e' piu' ambiguita'
    (nel BIP39 bastano sempre 4 lettere).
    """
    trovate = completa(prefisso, massimo=2)
    return trovate[0] if len(trovate) == 1 else None


# ---------------------------------------------------------------------------
# Il cuore: verifica del checksum BIP39
# ---------------------------------------------------------------------------
#
# Come funziona lo standard:
#   - ogni parola vale 11 bit (2048 = 2^11)
#   - 12 parole = 132 bit, 24 parole = 264 bit
#   - i primi bit sono l'entropia vera (128 o 256 bit)
#   - gli ultimi bit sono il checksum: i primi bit dello SHA-256 dell'entropia
#     (4 bit per 12 parole, 8 bit per 24 parole)
#
# Quindi l'ultima parola non e' libera: parte dei suoi bit sono obbligati.
# Ecco perche' le ultime parole valide sono 128 (frase da 12) oppure 8 (da 24).

def _impacchetta(indici):
    """Mette in fila i bit di tutte le parole: 11 bit ciascuna."""
    n_bit = len(indici) * 11
    buf = bytearray((n_bit + 7) // 8)
    pos = 0
    for idx in indici:
        for b in range(10, -1, -1):
            if (idx >> b) & 1:
                buf[pos >> 3] |= 0x80 >> (pos & 7)
            pos += 1
    return buf, n_bit


def _bit(buf, i):
    """Legge il bit numero i (contando da sinistra)."""
    return (buf[i >> 3] >> (7 - (i & 7))) & 1


def checksum_valido(indici):
    """True se la sequenza di numeri di parola forma una frase BIP39 valida."""
    n = len(indici)
    if n not in LUNGHEZZE_VALIDE:
        return False

    buf, n_bit = _impacchetta(indici)
    bit_checksum = n // 3            # 4 bit per 12 parole, 8 per 24
    bit_entropia = n_bit - bit_checksum

    entropia = bytes(buf[:bit_entropia // 8])
    atteso = hashlib.sha256(entropia).digest()

    for i in range(bit_checksum):
        if _bit(atteso, i) != _bit(buf, bit_entropia + i):
            return False
    return True


def frase_valida(parole):
    """Come sopra, ma partendo dalle parole scritte. Accetta lista o stringa."""
    if isinstance(parole, str):
        parole = parole.split()
    indici = []
    for p in parole:
        i = indice_di(p)
        if i is None:
            return False
        indici.append(i)
    return checksum_valido(indici)


def entropia_di(parole):
    """
    L'entropia contenuta nella frase, in byte. Serve ai test per confrontare
    il risultato con i vettori ufficiali. Il dispositivo non la mostra mai.
    """
    if isinstance(parole, str):
        parole = parole.split()
    indici = [indice_di(p) for p in parole]
    if None in indici or len(indici) not in LUNGHEZZE_VALIDE:
        raise ValueError("frase non valida")
    buf, n_bit = _impacchetta(indici)
    bit_entropia = n_bit - len(indici) // 3
    return bytes(buf[:bit_entropia // 8])


# ---------------------------------------------------------------------------
# La funzione principale del dispositivo
# ---------------------------------------------------------------------------

def _indici_di(parole_inserite):
    """Controlli comuni alle due versioni qui sotto."""
    if isinstance(parole_inserite, str):
        parole_inserite = parole_inserite.split()

    n_finale = len(parole_inserite) + 1
    if n_finale not in LUNGHEZZE_VALIDE:
        raise ValueError(
            "servono 11, 14, 17, 20 o 23 parole (ne hai date %d)"
            % len(parole_inserite))

    indici = []
    for p in parole_inserite:
        i = indice_di(p)
        if i is None:
            raise ValueError("parola non presente nel dizionario BIP39: %r" % p)
        indici.append(i)
    return indici


def ultime_parole_valide_riferimento(parole_inserite):
    """
    VERSIONE DI RIFERIMENTO: lenta ma ovvia da leggere.

    Prova tutte e 2048 le parole e tiene quelle che passano la verifica
    completa. Non e' quella che gira sul dispositivo, ma resta qui perche'
    e' il metro di paragone: il test controlla che la versione veloce dia
    esattamente gli stessi risultati di questa.
    """
    indici = _indici_di(parole_inserite)
    prova = indici + [0]
    valide = []
    for i in range(N_PAROLE):
        prova[-1] = i
        if checksum_valido(prova):
            valide.append(parola(i))
    return valide


def ultime_parole_valide(parole_inserite, avanzamento=None):
    """
    Date 11 (o 14, 17, 20, 23) parole, restituisce TUTTE le ultime parole
    che completano una frase valida.

    Restituisce una lista di parole:
        11 parole inserite -> 128 risultati
        23 parole inserite ->   8 risultati

    Non ne esiste una sola: l'ultima parola contiene sia bit di checksum
    (obbligati) sia bit di entropia (liberi). Sta all'utente scegliere.

    PERCHE' E' PIU' VELOCE DELLA VERSIONE DI RIFERIMENTO
    I bit delle parole gia' inserite non cambiano mai durante la ricerca:
    li calcoliamo una volta sola. Per ogni candidata riscriviamo soltanto
    gli 11 bit finali. Il controllo del checksum resta identico, riga per
    riga, a quello della funzione checksum_valido().

    'avanzamento' e' una funzione facoltativa, chiamata ogni tanto con un
    numero da 0 a 100: serve alla barra di avanzamento sullo schermo.
    """
    indici = _indici_di(parole_inserite)

    n = len(indici) + 1
    n_bit = n * 11
    bit_checksum = n // 3
    bit_entropia = n_bit - bit_checksum
    byte_entropia = bit_entropia // 8

    # i bit delle parole gia' inserite: calcolati UNA VOLTA
    buf = bytearray((n_bit + 7) // 8)
    pos = 0
    for idx in indici:
        for b in range(10, -1, -1):
            if (idx >> b) & 1:
                buf[pos >> 3] |= 0x80 >> (pos & 7)
            pos += 1

    # 'pos' e' ora il primo bit dell'ultima parola. Da qui in avanti la
    # memoria va ripulita a ogni tentativo: ne conservo una copia intatta.
    primo = pos >> 3
    coda_pulita = bytes(buf[primo:])

    valide = []
    for cand in range(N_PAROLE):
        buf[primo:] = coda_pulita          # azzera solo la parte finale
        p = pos
        for b in range(10, -1, -1):        # 11 bit invece di tutti
            if (cand >> b) & 1:
                buf[p >> 3] |= 0x80 >> (p & 7)
            p += 1

        atteso = hashlib.sha256(bytes(buf[:byte_entropia])).digest()
        ok = True
        for i in range(bit_checksum):
            if _bit(atteso, i) != _bit(buf, bit_entropia + i):
                ok = False
                break
        if ok:
            valide.append(parola(cand))

        if avanzamento is not None and (cand & 0xFF) == 0xFF:
            avanzamento(100 * (cand + 1) // N_PAROLE)

    if avanzamento is not None:
        avanzamento(100)
    return valide


# ---------------------------------------------------------------------------
# Pulizia
# ---------------------------------------------------------------------------

def dimentica(*strutture):
    """
    Sovrascrive e svuota le liste passate, per non lasciare le parole in giro
    in memoria piu' del necessario.

    ONESTA': in Python questa e' una precauzione, non una garanzia. Il
    linguaggio puo' aver lasciato copie delle stringhe altrove e non ce lo
    lascia controllare. La garanzia vera la da' il fatto che il dispositivo
    NON scrive nulla nella memoria permanente e che togliendo corrente la
    RAM si azzera. Chi vuole la cancellazione certa deve spegnere e riaccendere.
    """
    for s in strutture:
        try:
            for i in range(len(s)):
                s[i] = "        "
            del s[:]
        except (TypeError, AttributeError):
            pass
