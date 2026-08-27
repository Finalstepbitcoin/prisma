# Il file unico — note di lavoro

Ramo `uf2-unico`. Serve a produrre **un solo file** da trascinare sul
dispositivo, al posto di "carica MicroPython, poi copia dieci file col
terminale".

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
.venv-strumenti/bin/python prova_uf2.py    # 11 controlli, senza dispositivo
```

## La libreria in più

`crea_uf2.py` è l'unico pezzo del progetto che ha bisogno di
**littlefs-python** (BSD-3-Clause, involucro attorno alla libreria C
littlefs 2.11.2 — la stessa che gira dentro MicroPython sul dispositivo).

Va installata **solo nell'ambiente isolato**, mai nel Python di sistema, e
sempre verificando l'impronta del pacchetto:

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

## DA FARE: la prova sull'hardware

Tutto quello che si poteva verificare senza dispositivo è verificato
(`prova_uf2.py`, 11 controlli). Resta la prova vera:

1. tenere premuto BOOTSEL, collegare il cavo, trascinare `prisma-1.0.uf2`
2. il dispositivo deve **ripartire da solo** e mostrare `BLAST SAIL SPOIL`
3. controllare che i due modi funzionino (checksum e passphrase)
4. `python3 parla_col_pico.py elenco` deve elencare esattamente dieci file

Se qualcosa non va, il sintomo dice dove guardare:
- **si accende ma resta muto** → i parametri dell'archivio non combaciano
- **riparte in modo continuo** → problema nel firmware, non nell'archivio
- **tre parole diverse** → nell'archivio è finito qualcosa in più o in meno

Finché questa prova non è fatta, il ramo non va unito a `main`.
