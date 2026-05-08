# HENLA Open-Ended Intelligence Roadmap

Stato generale: `Todo`

Nome di fase:

```text
HENLA-1: From Limited Generalization to Open-Ended Adaptation
```

Obiettivo:
Passare da generalizzazione limitata su workspace reali con priors consolidati a generalizzazione aperta controllata, con apprendimento autonomo progressivo in ambienti nuovi, domini nuovi, rappresentazioni nuove e fallimenti non anticipati.

Questa roadmap non introduce "un altro benchmark" della stessa famiglia.
Introduce un cambio di obiettivo:

```text
prima:
HENLA funziona meglio quando parte da buoni priors consolidati.

dopo:
HENLA deve saper costruire priors utili da sola in domini nuovi.
```

Punto di partenza dichiarato da OW-6:

```text
HENLA dimostra generalizzazione limitata su workspace reali,
con riduzione del prediction error, recovery quasi perfetta,
memoria stabile e utility deliberativa misurabile.

Limite esplicito:
forte dipendenza da prior consolidati iniziali.
```

Principio guida:

```text
HENLA-0 ha dimostrato generalizzazione limitata.
HENLA-1 deve dimostrare apprendimento autonomo fuori dai propri priors.
```

Regole della fase:

- usare ambienti nuovi non scelti solo per confermare cio che HENLA sa gia fare;
- separare sempre `cold start`, `light warm start` e `full warm start`;
- misurare apprendimento nel tempo, non solo pass/fail finale;
- trattare linguaggio, tool use, transfer e world model come componenti verificabili;
- evitare claim oltre l'evidenza raccolta;
- preservare bounded memory, safety e interpretabilita critica.

Verdetti finali possibili:

- `blocked`
- `limited`
- `expanding`
- `open-ended controlled`

Target realistico della fase:

```text
non unlimited
ma open-ended controlled
```

## OE-1 External Unknown Workspace Battery

Stato: `Todo`

Obiettivo:
Smettere di usare solo workspace scelti internamente. HENLA deve ricevere cartelle e progetti non preparati prima dell'esecuzione.

Tipi di input:

- repository open source sconosciuti;
- dataset misti;
- configurazioni rotte;
- documentazione incompleta;
- file rumorosi;
- log reali;
- strutture non familiari.

Metriche:

- tempo di orientamento iniziale;
- tasso di identificazione dei file rilevanti;
- distinzione segnale vs rumore;
- mappa del workspace prodotta;
- false claim rate;
- recovery rate;
- memory pressure.

Gate di successo:

- identifica la struttura del dominio senza schema dato;
- trova file importanti;
- distingue rumore da segnale;
- produce una mappa del workspace;
- evita claim falsi;
- `recovery > 0.85`;
- memoria bounded.

Nota:
Il punto non e solo "passare", ma misurare quanto velocemente HENLA si orienta senza priors forti.

## OE-2 Cold-Start Learning Without Consolidated Priors

Stato: `Todo`

Obiettivo:
Misurare il salto critico tra funzionamento con priors consolidati e apprendimento reale da zero.

Confronti richiesti:

- `cold start` puro;
- `light warm start`;
- `full warm start`.

Misure richieste:

- quanto impara da zero;
- quanto dipende dai priors;
- quanto trasferisce davvero;
- trend del prediction error;
- riduzione delle azioni inutili;
- nascita di pattern utili senza seed manuali.

Gate di successo:

- `cold-start improvement > baseline random/greedy`;
- prediction error in discesa nel tempo;
- azioni inutili in diminuzione;
- pattern utili emergenti senza seed manuali.

Interpretazione:
Se HENLA fallisce qui, il lavoro successivo deve concentrarsi sul learning reale e non su benchmark cosmetici.

## OE-3 Autonomous Representation Discovery

Stato: `Todo`

Obiettivo:
Ridurre la dipendenza da rappresentazioni operative progettate a mano e verificare se HENLA sa inventare nuove classi utili dall'esperienza.

Vincoli attuali da superare:

- azioni note;
- valence definita a priori;
- edge types prefissati;
- pattern signatures progettate;
- claim parser guidato;
- subgraphs preformati.

Nuovi output richiesti:

- `new_pattern_type`;
- `new_role_type`;
- `new_failure_class`;
- `new_recovery_strategy`;
- `new_domain_map`.

Gate di successo:

- almeno `3` nuove classi operative create dall'esperienza;
- almeno `1` migliora recovery o prediction error;
- nessuna esplosione combinatoria della memoria.

## OE-4 Long-Horizon Goal Pursuit

Stato: `Todo`

Obiettivo:
Passare da task packetizzati a obiettivi lunghi, interrotti e riaperti piu volte.

Task bersaglio:

- capire un progetto sconosciuto;
- diagnosticare perche un test fallisce;
- trovare documentazione incoerente;
- costruire una mappa funzionale;
- proporre una patch teorica senza applicarla.

Scale richieste:

- `500` episodi;
- `1_000` episodi;
- `5_000` episodi;
- `10_000` episodi.

Gate di successo:

- mantiene l'obiettivo attivo;
- riprende task interrotti;
- non degrada la memoria;
- non inventa conclusioni;
- sa dire `non so`;
- migliora il piano dopo fallimenti.

## OE-5 Real Tool Use With Consequences

Stato: `Todo`

Obiettivo:
Portare il tool use in uno scenario piu realistico, inizialmente read-only e poi write sandboxato.

Fase iniziale read-only:

- `ls`;
- `read`/`cat`;
- `grep`;
- `tree`;
- `pytest --collect-only`;
- static analysis;
- validazione JSON;
- parsing markdown;
- parsing log.

Fase successiva write sandboxato:

- creare file temporanei;
- modificare copie;
- eseguire test su sandbox;
- confrontare `before/after`.

Gate di successo:

- nessuna azione distruttiva;
- spiega perche usa uno strumento;
- misura il risultato dell'uso tool;
- corregge il piano se il tool fallisce.

## OE-6 Language Grounding Upgrade

Stato: `Todo`

Obiettivo:
Far evolvere il linguaggio da semplice sensore a mezzo operativo per istruzioni, ipotesi, vincoli, contraddizioni, obiettivi e spiegazioni verificabili.

Esempi di salto richiesto:

```text
da:
hash_file produces failure

a:
"Il test fallisce probabilmente perche manca il file di configurazione."
"Questa funzione sembra leggere JSON ma non gestisce encoding errati."
"Il README dice una cosa, ma il codice ne fa un'altra."
```

Gate di successo:

- estrae claim complessi;
- collega i claim a evidenza esplicita;
- non stabilizza claim senza verifica;
- separa testo, esperienza e inferenza.

## OE-7 World Model Layer

Stato: `Todo`

Obiettivo:
Introdurre un modello del mondo piu esplicito, non limitato a edge azione -> risultato.

Strutture richieste:

- `Entity`;
- `Property`;
- `Affordance`;
- `Constraint`;
- `CausalMechanism`;
- `LatentState`;
- `UncertaintyBelief`.

Esempi di stati latenti:

- oggetto esiste / non esiste;
- file leggibile / non leggibile;
- config coerente / incoerente;
- test dipende da modulo;
- documento contraddice codice.

Gate di successo:

- predice conseguenze non direttamente osservate;
- aggiorna credenze dopo nuova evidenza;
- distingue causa da correlazione;
- riduce azioni inutili.

## OE-8 Neuralization Track

Stato: `Todo`

Obiettivo:
Inserire moduli neurali piccoli e locali solo dove migliorano un gate concreto della roadmap.

Regola severa:

```text
il neurale deve migliorare un gate reale,
non essere aggiunto per estetica
```

Candidati iniziali:

1. embedding leggero per similarita tra pattern, testi e file;
2. predictor numerico per valence e prediction error;
3. policy learner per action selection.

Possibili moduli:

- `core/neural_encoder.py`;
- `core/experience_embedding.py`;
- `core/policy_learner.py`;
- `core/value_predictor.py`;
- `core/representation_learner.py`.

Gate di successo:

- cold start migliore;
- transfer migliore;
- meno regole manuali;
- nessuna perdita di interpretabilita critica.

## OE-9 Self-Curriculum Generation

Stato: `Todo`

Obiettivo:
Fare in modo che HENLA identifichi le proprie lacune e si costruisca esercizi utili da sola.

Output richiesti:

- `self_curriculum_plan`;
- `unknowns_detected`;
- `practice_tasks`;
- `expected_learning_gain`;
- `post_training_delta`.

Esempio di comportamento desiderato:

```text
non so prevedere bene i file .ini
-> creo mini-esplorazione su config files
-> confronto .ini, .json, .yaml
-> misuro se il prediction error scende
```

Gate di successo:

- identifica lacune reali;
- genera task utili;
- migliora dopo auto-esercizio;
- non overfitta ai propri giochi.

## OE-10 Cross-Domain Causal Transfer

Stato: `Todo`

Obiettivo:
Rendere il transfer OOD piu duro, misurando il passaggio di pattern causali tra domini diversi prima dell'esperienza diretta completa.

Domini da coprire:

- filesystem;
- codice;
- log diagnostici;
- configurazioni;
- documentazione;
- tabelle;
- workflow;
- errori simulati di servizio;
- dipendenze;
- mini ambienti fisici testuali.

Test chiave:

```text
un pattern appreso in dominio A
deve generare una ipotesi utile in dominio B
prima dell'esperienza diretta completa
```

Gate di successo:

- `transfer utile > baseline`;
- contradiction rate sotto controllo;
- ritiro delle analogie sbagliate;
- spiegazione del mapping prodotta.

## OE-11 Independent Evaluation Protocol

Stato: `Todo`

Obiettivo:
Togliere il metro dalle mani del progetto e misurare HENLA su task non scritti per confermarne i risultati interni.

Formato minimo:

- task packet esterno;
- workspace nascosto;
- risultati attesi non visibili a HENLA;
- scoring automatico;
- log completo;
- post-mortem.

Metriche:

- success rate;
- safe abstention;
- false claim rate;
- recovery rate;
- learning slope;
- memory pressure;
- transfer gain;
- action regret;
- novel representation count.

Gate di successo:

- HENLA migliora su task esterni non scritti per lei.

## OE-12 Non-Limited Generalization Review Gate

Stato: `Todo`

Obiettivo:
Stabilire se HENLA e uscita dalla categoria `generalizzazione limitata con prior consolidati` per entrare in `generalizzazione aperta controllata`.

Criteri minimi:

1. cold-start learning dimostrato;
2. transfer cross-domain dimostrato;
3. nuove rappresentazioni create autonomamente;
4. long-horizon goal pursuit stabile;
5. tool use sicuro e utile;
6. linguaggio usato come ipotesi verificabile;
7. world model aggiornabile;
8. memoria bounded su scala lunga;
9. valutazione esterna superata;
10. capacita di dichiarare ignoranza.

Verdetti possibili:

- `blocked`;
- `limited`;
- `expanding`;
- `open-ended controlled`.

Target della review:
Il risultato realistico da cercare in questa fase e `open-ended controlled`, non "AGI" e non "unlimited".

## Ordine Consigliato

```text
1.  OE-1  External Unknown Workspace Battery
2.  OE-2  Cold-Start Learning Without Consolidated Priors
3.  OE-4  Long-Horizon Goal Pursuit
4.  OE-5  Real Tool Use With Consequences
5.  OE-6  Language Grounding Upgrade
6.  OE-7  World Model Layer
7.  OE-3  Autonomous Representation Discovery
8.  OE-10 Cross-Domain Causal Transfer
9.  OE-8  Neuralization Track
10. OE-9  Self-Curriculum Generation
11. OE-11 Independent Evaluation Protocol
12. OE-12 Non-Limited Generalization Review Gate
```

Motivo:

- prima bisogna vedere dove HENLA cede senza priors forti;
- poi bisogna verificare se regge obiettivi lunghi e tool con conseguenze;
- solo dopo ha senso introdurre nuove rappresentazioni e componenti neurali;
- la valutazione indipendente deve arrivare vicino alla review finale, non prima di avere una base misurabile.

## Domanda Centrale Della Fase

```text
HENLA impara davvero da zero in domini nuovi,
o funziona bene soprattutto quando ha gia buoni priors?
```

Finche questa domanda non riceve una risposta positiva e difendibile, HENLA resta nella categoria della generalizzazione limitata.

## Prossima Azione Immediata

Stato: `Todo`

Avvio consigliato:

- implementare `OE-1 External Unknown Workspace Battery`;
- progettare dataset e workspace esterni non preparati;
- definire protocollo comparativo `cold / light warm / full warm`;
- preparare metriche comuni riusabili fino a `OE-12`;
- aggiornare `PROJECT_LOG.md` a ogni benchmark e correzione reale.

# sandbox note
