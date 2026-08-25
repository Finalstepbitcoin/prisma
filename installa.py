#!/usr/bin/env python3
"""
installa.py  --  Final Step Bitcoin / Sintesi

Copia sul dispositivo tutti i file che gli servono, in un colpo solo.

GIRA SUL MAC, dopo aver caricato MicroPython sul Pico.

Uso:
    python3 installa.py
"""

import subprocess
import sys

# I file che vanno sul dispositivo. QUESTA LISTA E' LA STESSA usata da
# prepara_impronta.py: se le due divergono, l'impronta calcolata sul
# computer non corrispondera' a quella mostrata dal dispositivo.
FILE_DISPOSITIVO = (
    "wordlist.py",
    "bip39_checksum.py",
    "diceware.py",
    "diceware_en.py",
    "diceware_it.py",
    "qr_canale.py",
    "impronta.py",
    "schermo.py",
    "interfaccia.py",
    "main.py",
)


def main():
    print("Preparo %d file sul dispositivo: li copia e ne verifica il" % len(FILE_DISPOSITIVO))
    print("contenuto, ma non sostituisce ancora nessun file attivo.\n")
    for nome in FILE_DISPOSITIVO:
        esito = subprocess.run([sys.executable, "parla_col_pico.py", "prepara", nome],
                               capture_output=True, text=True)
        if esito.returncode != 0:
            print("ERRORE preparando %s:" % nome)
            print(esito.stdout, esito.stderr)
            print("\nNessun file attivo sul dispositivo e' stato toccato: sta ancora")
            print("girando esattamente la versione precedente. Risolvi il problema")
            print("e rilancia python3 installa.py.")
            return 1
        ultima = [r for r in esito.stdout.splitlines() if "Verificato" in r]
        print("  %-20s %s" % (nome, ultima[0] if ultima else "ok"))

    print("\nTutti i file sono pronti e verificati. Attivazione (un'operazione")
    print("di filesystem, non un trasferimento: dura una frazione di secondo")
    print("per tutti i file insieme)...")
    esito = subprocess.run([sys.executable, "parla_col_pico.py", "attiva"]
                           + list(FILE_DISPOSITIVO),
                           capture_output=True, text=True)
    if esito.returncode != 0:
        print("ERRORE nell'attivazione:")
        print(esito.stdout, esito.stderr)
        print("\nAlcuni file potrebbero essere stati sostituiti e altri no.")
        print("Rilancia SUBITO python3 installa.py per completare: e' sicuro,")
        print("rifara' solo i passaggi mancanti, non danneggia nulla.")
        return 1
    print("  " + esito.stdout.strip())

    print("\nVerifica finale: ogni file installato corrisponde davvero a")
    print("quello sul computer? (contenuto per contenuto, non solo che")
    print("qualcosa con quel nome esista)")
    problemi = 0
    for nome in FILE_DISPOSITIVO:
        esito = subprocess.run([sys.executable, "parla_col_pico.py", "verifica", nome],
                               capture_output=True, text=True)
        riga = esito.stdout.strip().splitlines()
        print("  %s" % (riga[-1] if riga else "%s: errore sconosciuto" % nome))
        if esito.returncode != 0:
            problemi += 1
    if problemi:
        print("\n%d file NON corrispondono al manifest atteso. Rilancia" % problemi)
        print("python3 installa.py per completare, non e' un'operazione distruttiva.")
        return 1

    print("\nControllo che non siano rimasti file non previsti sul dispositivo...")
    presenti = elenco_dispositivo()
    if presenti is None:
        return 1
    attesi = set(FILE_DISPOSITIVO)
    # QUALUNQUE nome non previsto, non solo i .py: l'impronta misura tutti i
    # file, di ogni estensione, e MicroPython sa caricare anche i .mpy. Un
    # nome che compare qui e non e' un file puo' essere una CARTELLA (per
    # esempio /lib): l'elenco mostra solo il primo livello, ma basta vederla
    # per sapere che c'e' qualcosa da guardare.
    estranei = sorted(n for n in presenti
                      if n not in attesi and not n.endswith(".tmp"))
    residui = sorted(n for n in presenti if n.endswith(".tmp"))
    if estranei:
        print("\nATTENZIONE: sul dispositivo c'e' roba non prevista:")
        for n in estranei:
            print("  - %s" % n)
        print("Cambia l'impronta del firmware, quindi il dispositivo mostrera'")
        print("tre parole diverse da quelle pubblicate. Va rimossa: se e' un")
        print("file con os.remove, se e' una cartella va svuotata e poi tolta")
        print("con os.rmdir.")
    if residui:
        print("\nATTENZIONE: residui di una preparazione mai completata (una")
        print("copia interrotta prima di questa installazione):")
        for n in residui:
            print("  - %s" % n)
        print("Non vengono eseguiti, ma SONO CONTATI NELL'IMPRONTA come")
        print("qualunque altro file: finche' restano li', le tre parole")
        print("mostrate all'accensione non saranno quelle pubblicate.")
        print("Vanno tolti, per esempio con:")
        for n in residui:
            print("    python3 parla_col_pico.py esegui \"import os; os.remove(%r)\"" % n)
    if not estranei and not residui:
        print("  nessun file estraneo.")

    print("\nFatto: %d file installati e verificati. Stacca e riattacca il cavo,"
          % len(FILE_DISPOSITIVO))
    print("deve partire da solo.")
    return 0


def elenco_dispositivo():
    """Tutti i nomi presenti sul dispositivo, ripulendo l'output del comando."""
    esito = subprocess.run([sys.executable, "parla_col_pico.py", "elenco"],
                           capture_output=True, text=True)
    if esito.returncode != 0:
        print("ERRORE leggendo l'elenco dal dispositivo:")
        print(esito.stdout, esito.stderr)
        return None
    return [r.strip() for r in esito.stdout.splitlines() if r.strip()]


if __name__ == "__main__":
    sys.exit(main())
