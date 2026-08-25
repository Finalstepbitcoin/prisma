# Le liste originali, archiviate qui

In questa cartella ci sono le **liste di parole Diceware così come sono state
scaricate** dalle pagine dei loro autori, senza nessuna modifica: sono i file
da cui `prepara_diceware.py` genera `diceware_en.py` e `diceware_it.py`, cioè
quello che poi finisce dentro il dispositivo.

## Perché stanno qui

Due motivi, tutti e due pratici.

**Perché il firmware sia ricostruibile anche fra dieci anni.** Se un giorno il
sito di un autore non c'è più, senza queste copie non sarebbe più possibile
rigenerare il firmware né controllare che quello installato corrisponda al
sorgente. La verifica del dispositivo si regge tutta su questa possibilità.

**Perché la licenza lo chiede.** Il firmware assemblato contiene la lista
italiana, che è GPL-3.0. Chi riceve un dispositivo già pronto deve poter
ottenere il sorgente corrispondente: adesso è qui, insieme al codice.

Attenzione, le copie **non sostituiscono la verifica**: `prepara_diceware.py`
scarica sempre dalla fonte originale e usa questi file solo se il download non
riesce. In tutti e due i casi confronta lo SHA-256 con quello scritto nel
codice, e si ferma se non corrisponde. La copia archiviata è una rete di
sicurezza, non una scorciatoia.

## Cosa c'è

### `diceware-inglese-reinhold.asc`

| | |
|---|---|
| Autore | Arnold Reinhold, che il metodo Diceware l'ha inventato nel 1995 |
| Licenza | **CC-BY 4.0** — uso commerciale permesso, serve l'attribuzione |
| Pagina | <https://theworld.com/~reinhold/diceware.html> |
| File | <https://theworld.com/~reinhold/diceware.wordlist.asc> |
| SHA-256 | `3cd6164a99e95381f8620aec782a933545bcd5833fa331d267a6829f6665256e` |
| Voci | 7776 |

Reinhold concede la lista inglese sotto CC-BY 4.0. Il *testo della sua pagina*
è invece CC-BY-NC-ND, cioè non commerciale: è una distinzione da non
confondere, qui si usa la lista.

### `diceware-italiana-gamberini-v4.txt`

| | |
|---|---|
| Autore | Tarin Gamberini |
| Licenza | **GPL-3.0-or-later** (testo completo in `COPYING-GPL-3.0.txt`) |
| Pagina | <https://www.taringamberini.com/it/diceware_it_IT/lista-di-parole-diceware-in-italiano/> |
| File | versione 4, `word_list_diceware_it-IT-4.txt` |
| SHA-256 | `b441559b64fb7041b9bbcecb3c43111f2523ec84e172670409f40c462eda0b93` |
| Voci | 7776 |

Non è la traduzione di quella inglese: è una lista a sé, e lo stesso tiro di
dadi dà una parola diversa nelle due liste.

### `COPYING-GPL-3.0.txt`

Il testo completo della licenza GPL-3.0, scaricato da
<https://www.gnu.org/licenses/gpl-3.0.txt>. Vale per la lista italiana e per
il firmware che la contiene.

## Cosa NON cambia

Il codice di questo progetto resta sotto licenza **MIT** (vedi `LICENSE`).
I file di questa cartella non sono nostri e restano di chi li ha fatti, ognuno
con la propria licenza. Il firmware assemblato, contenendo la lista italiana,
esce sotto **GPL-3.0**: è scritto in `LICENZE-TERZI.md`.

Il dizionario BIP39 inglese non sta qui: fa parte della specifica pubblica di
Bitcoin e si scarica dal repository ufficiale dei BIP, che non è il sito
personale di nessuno.

## Se una lista viene aggiornata dall'autore

Non basta sostituire il file. La procedura è:

1. scaricare la nuova versione e **guardarla**, confrontandola con la vecchia;
2. aggiornare `impronta_attesa` dentro `prepara_diceware.py`;
3. sostituire il file in questa cartella e aggiornare lo SHA-256 qui sopra;
4. rilanciare `prepara_diceware.py`, `test_diceware.py` e `installa.py`;
5. rifare la guida con `guida/build.sh`: cambiando la lista cambia il
   firmware, e quindi cambiano le tre parole dell'impronta stampate sul
   foglio. `build.sh` da solo si rifiuta di stampare se non le si aggiorna.
