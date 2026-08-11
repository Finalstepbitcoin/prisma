# Custodia da stampare in 3D

Tre file, ma **il primo da stampare è uno solo**.

| File | Cosa è | Tempo di stampa |
|---|---|---|
| `prova_incastro.stl` | cornice bassa, serve solo a provare se il dispositivo entra | ~10 minuti |
| `vassoio.stl` | la scocca inferiore, quella che tiene tutto | ~2 ore |
| `cornice.stl` | l'anello superiore che blocca il display | ~20 minuti |

## Come procedere

**1. Stampa `prova_incastro.stl`.** È una cornice alta 3 mm: dieci minuti e
poca plastica. Prova a infilarci il dispositivo montato.

- se **entra con un po' di attrito**: perfetto, vai avanti
- se **è troppo stretto**: apri `genera_case.py`, alza `GIOCO` da `0.4` a `0.6`,
  rilancia `python3 genera_case.py` e ristampa la prova
- se **balla**: abbassa `GIOCO` a `0.25`

**2. Misura tre cose** sul dispositivo montato, con un righello:

| Cosa | Valore ora nel file | Variabile |
|---|---|---|
| altezza del pacco, di taglio (dal fondo del Pico al vetro) | 15,0 mm | `ALTEZZA_PACCO` |
| larghezza del connettore micro-USB | 8,5 mm | `USB_LARGHEZZA` |
| a che altezza dal fondo comincia il connettore | 1,0 mm | `USB_DAL_FONDO` |

Se differiscono, correggile in cima a `genera_case.py` e rigenera.

**3. Stampa `vassoio.stl` e `cornice.stl`.**

## Impostazioni di stampa consigliate

- **PLA arancione** — l'arancione Bitcoin è `#F7931A`
- altezza strato **0,2 mm**
- riempimento **20%**
- **niente supporti**: la custodia è disegnata apposta per non averne bisogno
- il vassoio va stampato **col fondo appoggiato al piano**

## Il colore

Un file `.stl` contiene **solo la forma**, non il colore: l'arancione lo dà il
filamento che carichi nella stampante. Non c'è niente da impostare nel file.

## Se vuoi modificarla

`genera_case.py` non richiede nessun programma di modellazione né alcuna
libreria: la custodia è fatta di soli parallelepipedi, quindi è scritta
direttamente in Python. Tutte le quote stanno in cima al file, con il nome
per esteso e il commento che dice a cosa servono.

```bash
python3 genera_case.py
```
