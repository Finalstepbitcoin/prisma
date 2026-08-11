# Licenze e attribuzioni

Questo progetto usa liste di parole e idee di altre persone. Qui c'è scritto
di chi sono e a quali condizioni si possono usare.

**Nessuna di queste liste è inclusa in questo repository.** Gli script
`prepara_wordlist.py` e `prepara_diceware.py` le scaricano dalle fonti
originali al momento della compilazione. Così il codice di questo progetto
resta tutto sotto licenza MIT, e ogni lista resta sotto la propria.

---

## Dizionario BIP39 (inglese, 2048 parole)

- **Fonte**: [repository ufficiale dei BIP](https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt)
- **Standard**: [BIP-39](https://github.com/bitcoin/bips/blob/master/bip-0039/bip-0039.mediawiki)
- Fa parte della specifica pubblica di Bitcoin.

## Lista Diceware inglese (7776 voci)

- **Autore**: Arnold Reinhold, che il metodo Diceware l'ha inventato nel 1995
- **Licenza**: **CC-BY 4.0** — uso commerciale permesso, serve l'attribuzione
- **Pagina**: <https://theworld.com/~reinhold/diceware.html>

Sulla sua pagina Reinhold scrive che concede i diritti sulla lista inglese
sotto CC-BY 4.0. Attenzione a non confondersi: il *testo della pagina* è invece
CC-BY-NC-ND, cioè non commerciale. È la lista che ci interessa, ed è quella
permissiva.

## Lista Diceware italiana (7776 voci)

- **Autore**: Tarin Gamberini
- **Licenza**: **GPL-3.0-or-later** per la versione testuale
- **Pagina**: <https://www.taringamberini.com/it/diceware_it_IT/lista-di-parole-diceware-in-italiano/>

Non è la traduzione di quella inglese: è una lista a sé, e lo stesso numero di
dadi dà una parola diversa nelle due liste.

## Motore dei calcoli

La logica del checksum BIP39 deriva da **[embit](https://github.com/diybitcoinhardware/embit)**
(licenza MIT), una libreria Bitcoin pensata per i sistemi embedded. È la stessa
libreria usata sia da [SeedSigner](https://github.com/SeedSigner/seedsigner) sia
da [Krux](https://github.com/selfcustody/krux).

I vettori di test provengono da
**[trezor/python-mnemonic](https://github.com/trezor/python-mnemonic)**, l'implementazione
di riferimento dello standard.

## MicroPython

Il dispositivo esegue [MicroPython](https://micropython.org/) (licenza MIT).

---

## Cosa significa in pratica

**Il codice di questo repository è MIT**: chiunque può prenderlo e farne quello
che vuole, anche a scopo commerciale, mantenendo l'avviso di copyright.

**Un firmware assemblato che includa la lista italiana esce sotto GPL-3.0**,
perché quella lista è GPL. In pratica questo obbliga chi lo distribuisce a
fornire i sorgenti e a permettere all'acquirente di installare una versione
modificata — cioè esattamente quello che questo progetto promette comunque.

Un firmware con la sola lista inglese non ha questo vincolo: MIT e CC-BY
bastano.
