# Il file unico — note di lavoro

Serve a produrre **un solo file** da trascinare sul dispositivo, al posto
di "carica MicroPython, poi copia dieci file col terminale".

Nato sul ramo `uf2-unico`, portato qui il 27 agosto 2026 dopo la prima
prova su hardware vero.

## Cosa c'è di nuovo

| File | Cosa fa |
|---|---|
| `crea_uf2.py` | costruisce `prisma-<versione>.uf2` |
| `prova_uf2.py` | rilegge il file prodotto e controlla che dentro ci sia il giusto |

Non è stata toccata **nessuna riga** del programma che gira sul dispositivo:
cambia solo il modo in cui i file ci arrivano dentro.

## Come si usa

```bash
.venv-strumenti/bin/python crea_uf2.py     # produce prisma-1.0.uf2
.venv-strumenti/bin/python prova_uf2.py    # 12 controlli, senza dispositivo
```

## La libreria in più

`crea_uf2.py` è l'unico pezzo del progetto che ha bisogno di
**littlefs-python** (BSD-3-Clause, involucro attorno alla libreria C
littlefs 2.11.2 — la stessa che gira dentro MicroPython sul dispositivo).

Va installata **solo nell'ambiente isolato**, mai nel Python di sistema, e
sempre verificando l'impronta del pacchetto. I comandi qui sotto sono per
**Mac con chip Apple**: su un altro sistema cambia il nome del pacchetto, e
con esso l'impronta da confrontare — quella giusta si prende dalla pagina
del progetto su PyPI.

```bash
python3 -m venv .venv-strumenti
curl -o littlefs_python-0.19.0-cp314-cp314-macosx_11_0_arm64.whl \
  https://files.pythonhosted.org/packages/26/12/ab923553e4894fbf44f4692d6c5898c1e66f41e57ff7a73b90e8aa0fb6f5/littlefs_python-0.19.0-cp314-cp314-macosx_11_0_arm64.whl
shasum -a 256 littlefs_python-0.19.0-cp314-cp314-macosx_11_0_arm64.whl
#  deve dare: d054ac280541afdae5722fb8d7ebc0e121d822c33d95d57889fd8fab2a211486
.venv-strumenti/bin/pip install --no-index --no-deps littlefs_python-*.whl
```

Non serve né a chi compra il dispositivo né a chi vuole solo verificare i
calcoli: quelli restano due comandi con la sola libreria standard di Python.

## I parametri dell'archivio: da dove vengono

Non sono stati indovinati. Vengono dalla sorgente ufficiale di MicroPython e
devono combaciare **esattamente**, altrimenti il dispositivo si accende e non
trova niente:

| Valore | Da dove | Quanto |
|---|---|---|
| dimensione archivio | `ports/rp2/boards/RPI_PICO2/mpconfigboard.cmake` | 3.145.728 byte (3 MB) |
| inizio archivio | `ports/rp2/rp2_flash.c` (4 MB − 3 MB) | 1 MB, cioè `0x10100000` |
| blocco | `ports/rp2/rp2_flash.c`, `FLASH_SECTOR_SIZE` | 4096 byte |
| scrittura | `ports/rp2/modules/_boot.py`, `VfsLfs2(bdev, progsize=256)` | 256 byte |

Il firmware finisce a 320 KB, l'archivio comincia a 1024 KB: in mezzo restano
i dati di collaudo che il Raspberry Pi scrive in fabbrica a 508 KB, che non
vengono né scritti né misurati.

## Due cose che è importante sapere

**L'immagine è sempre identica a parità di file.** Ricostruita tre volte di
fila dà lo stesso SHA-256: chiunque può rifare il file e ottenere il nostro,
byte per byte. Senza questa proprietà l'intera storia della verifica non
starebbe in piedi.

**Le tre parole dell'impronta non cambiano.** L'impronta misura MicroPython
(che resta intatto) e i dieci file (che sono gli stessi): un dispositivo
caricato col file unico è indistinguibile da uno installato col metodo
vecchio. `prova_uf2.py` lo verifica.

## Perché il file è da 1 MB e non da 6

littlefs sparge i file in giro per l'archivio invece di metterli in fila —
lo fa apposta, per non consumare sempre le stesse celle. Scrivendo tutto il
tratto dal primo all'ultimo blocco usato ci porteremmo dietro 2,4 MB di
vuoto. Siccome ogni blocco `.uf2` si porta dietro il proprio indirizzo, si
scrivono solo i blocchi che contengono qualcosa.

È sicuro anche rispetto a un'installazione precedente: il caricatore del Pico
cancella l'intero settore da 4096 byte prima di scriverne anche un pezzo, e
l'elenco dei file (i primi due blocchi) viene riscritto per intero, quindi
niente di vecchio resta raggiungibile.

## La prova sull'hardware: fatta il 27 agosto 2026

Caricato su un Pico 2 vero: il disco si smonta da solo, il dispositivo
riparte e mostra `Prisma 1.0` con le tre parole dell'impronta.

**La prima prova ha bocciato il file**, ed e' servita esattamente a questo.
Il dispositivo restava fermo in BOOTSEL: il file veniva scritto per intero,
nessun errore da nessuna parte, ma niente riavvio. Il motivo era la
numerazione dei blocchi, che il caricatore conta **per famiglia** e non su
tutto il file (il dettaglio sta nel commento dentro `crea_uf2.py`). I dodici
controlli passavano lo stesso, perche' due di essi pretendevano proprio la
regola sbagliata: sono stati riscritti.

Se un domani qualcosa non andasse, il sintomo dice dove guardare:

- **il disco resta montato e non riparte** → la numerazione dei blocchi
- **si accende ma resta muto** → i parametri dell'archivio non combaciano
- **riparte in modo continuo** → problema nel firmware, non nell'archivio
- **tre parole diverse da quelle attese** → nell'archivio e' finito qualcosa
  in piu' o in meno

**Su macOS il file va trascinato dal Finder**, non copiato da terminale:
`cp` scrive i settori in un ordine che il caricatore non accetta, non da'
errore, e il dispositivo resta fermo senza che nulla lo segnali.
