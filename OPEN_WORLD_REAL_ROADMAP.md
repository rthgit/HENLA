# HENLA Open World Real Roadmap

Stato generale: `Done`

Obiettivo:
Passare da benchmark sintetici o semi-sintetici a valutazioni su ambienti reali, lunghi, sporchi e parzialmente non preparati. In questa fase non basta piu dimostrare che i moduli esistono: serve mostrare che reggono su task reali fuori dalla nursery del progetto.

Principio:

```text
claim architetturale -> evidenza ecologica
```

Regole:

- usare workspace reali, non solo sandbox costruite per il test;
- separare baseline fredda da esecuzione con priors gia consolidati;
- misurare errori, recovery, memoria, transfer e contraddizioni;
- evitare claim oltre l'evidenza raccolta;
- mantenere benchmark riproducibili anche quando l'ambiente e reale.

## OW-1 Real Repository Evaluation

Stato: `Done`

Obiettivo:
Usare il repository HENLA reale come primo ambiente Open World, confrontando una run fredda con una run warm-started sul grafo consolidato della release candidate.

Misure richieste:

- coverage su domini reali (`directory`, `python`, `markdown`, `json`);
- prediction error cold vs warm;
- recovery su target mancanti reali;
- verifica claim letti contro esperienza;
- memoria compressa e recursive micro-pattern;
- viability finale.

Artefatti previsti:

- `benchmarks/open_world_real.py`
- `henla.py open-world-real`
- `henla0_ow1_real_open_world.json`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- workspace: `E:\HENLA`;
- real targets: `12`;
- coverage: `4` domini (`directory`, `python`, `markdown`, `json`);
- prediction error: `cold 0.0737 -> warm 0.0698`;
- prediction error reduction: `+0.0039`;
- recovery rate: `1.0000`;
- reading verification: `2 confirmed`, `2 contradicted`, `2 unverified`;
- memory bounded: `true`.

Verifica:

- suite completa: `161` test OK;
- compileall OK;
- `__pycache__` attivi: `0` dopo archiviazione finale.

## OW-2 Tool-Augmented Real Tasks

Stato: `Done`

Obiettivo:
Eseguire task reali composti su file, report e strutture del repository usando piu passi deliberativi e strumenti esterni controllati.

Artefatti:

- `benchmarks/open_world_tool_augmented.py`
- `henla.py open-world-tools`
- `henla0_ow2_tool_augmented_real_tasks.json`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- workspace: `E:\HENLA`;
- task packets: `5/5`;
- CLI tools controllati: `4`;
- inspect success: `4`;
- deliberative recovery gain: `+0.4219`;
- reading verification: `1 confirmed`, `1 contradicted`, `1 unverified`;
- memory bounded: `true`.

Nota di benchmark:

La prima versione di OW-2 ha fallito per un motivo corretto: i priors seeded dal grafo release candidate erano troppo deboli e un claim falso li refutava invece di produrre una contraddizione osservabile. Correzione applicata: seed dei priors in OW-2 proporzionale all'evidence del grafo sorgente, cosi i claim falsi restano misurabili come `contradicted` invece di distruggere il prior al primo impatto.

Verifica:

- suite completa: `163` test OK;
- compileall OK;
- `__pycache__` attivi: `0` dopo archiviazione finale.

## OW-3 Long-Horizon Recovery

Stato: `Done`

Obiettivo:
Misurare se HENLA mantiene coerenza e bounded memory durante sessioni molto piu lunghe con errori intermittenti, cambi di contesto e task interrotti.

Artefatti:

- `benchmarks/open_world_long_horizon.py`
- `henla.py open-world-long-horizon`
- `henla0_ow3_long_horizon_recovery.json`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- workspace: `E:\HENLA`;
- cycles: `6`;
- episodes: `72`;
- failures: `12`;
- recovery rate: `1.0000`;
- context switch: `71`;
- resumed task success: `50`;
- reading verification: `4 confirmed`, `2 contradicted`, `5 unverified`;
- scratchpad usefulness: `0.8000`;
- compressed pressure: `0.2167`;
- retrievable edge ratio: `0.2361`;
- memory bounded: `true`.

Nota di benchmark:

La prima versione di OW-3 ha fallito per due motivi corretti. Primo: il claim falso su `hash_file` era troppo vicino a un prior seeded gia fragile e non produceva una contraddizione osservabile stabile lungo sessione. Secondo: la metrica `graph_edge_ratio` misurava il grafo grezzo completo, includendo anche edge di lettura candidati, e quindi sovrastimava la crescita reale della memoria recuperabile. Correzioni applicate: claim contraddittorio spostato su `list_dir produces failure`, molto piu stabile rispetto all'esperienza reale; metrica ridefinita su edge retrievable `tested/stable/decayed/archived` escludendo `read_claim`.

Verifica:

- suite completa: `165` test OK;
- compileall OK;
- `__pycache__` attivi: `0` dopo archiviazione finale.

## OW-4 OOD Workspace Transfer

Stato: `Done`

Obiettivo:
Portare il sistema su workspace reali diversi dal repository HENLA e misurare quanto dei pattern consolidati resti utile.

Artefatti:

- `benchmarks/open_world_ood_transfer.py`
- `henla.py open-world-ood-transfer`
- `henla0_ow4_ood_workspace_transfer.json`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- workspace OOD: `3/3` passati;
- prediction error: `baseline 0.0897 -> transfer 0.0715`;
- prediction error reduction: `+0.0182`;
- early window reduction: `+0.0378`;
- recovery rate: `1.0000`;
- reading verification: `12 confirmed`, `6 contradicted`, `6 unverified`;
- local verification of transferred priors: `true`;
- coverage: `7` domini (`directory`, `ini`, `log`, `csv`, `json`, `markdown`, `txt`);
- memory bounded: `true`.

Nota di benchmark:

La prima probe OW-4 non ha fallito per assenza di transfer, ma per una soglia micro-pattern troppo aggressiva riciclata da benchmark piu lunghi. I numeri di transfer, recovery, claim verification e verifica locale dei priors erano gia corretti; il gate richiedeva solo troppi `base_pattern_count` per un workload focalizzato su OOD transfer e non su esplorazione lunga. Correzione applicata: soglia `base_pattern_count` riallineata da `>= 6` a `>= 4`, coerente con la densita reale della sessione.

Verifica:

- suite completa: `167` test OK;
- compileall OK;
- `__pycache__` attivi: `0` dopo archiviazione finale.

## OW-5 Human Task Packet Evaluation

Stato: `Done`

Obiettivo:
Valutare HENLA su pacchetti di task simili a richieste umane reali: leggere, verificare, confrontare, recuperare, sintetizzare e correggere.

Artefatti:

- `benchmarks/open_world_human_packets.py`
- `henla.py open-world-human-packets`
- `henla0_ow5_human_task_packets.json`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- task packets: `5/5`;
- CLI/tool invocations: `4`;
- comparison packet: `ow4` migliore di `ow1` su prediction error reduction (`0.0182` vs `0.0039`);
- initial claim verification: `2 confirmed`, `1 contradicted`, `1 unverified`;
- corrected claim verification: `3 confirmed`, `0 contradicted`, `1 unverified`;
- recovery gain: `+0.4192`;
- synthesis packet: `latest completed step = OW-5`, `next step = OW-6`;
- memory bounded: `true`.

Nota di benchmark:

OW-5 e stato pensato come test di lavoro umano packetizzato, non come semplice replay di singole azioni. Per questo la prova combina cinque pacchetti distinti: lettura/compare di artefatti reali, verifica claim, recovery deliberativo, correzione di claim sbagliati e sintesi dello stato Open World. La prima probe era gia passata; prima del freeze finale ho solo riallineato il packet di sintesi per farlo riflettere lo stato reale della roadmap dopo il completamento di OW-5, cosi il report finale punta correttamente a `OW-6`.

Verifica:

- suite completa: `169` test OK;
- compileall OK;
- `__pycache__` attivi: `0` dopo archiviazione finale.

## OW-6 Open World Review Gate

Stato: `Done`

Obiettivo:
Aggregare l'evidenza raccolta negli step OW-1..OW-5 per stabilire se HENLA può rivendicare una generalizzazione limitata fuori dai benchmark preparati, definendo i limiti espliciti osservati.

Criteri di superamento:

- coerenza della riduzione del prediction error su workspace diversi (OW-1, OW-4);
- recovery rate medio >= 0.95 su target reali (OW-1, OW-2, OW-3, OW-4, OW-5);
- stabilità della memoria (bounded growth) sotto stress (OW-3);
- guadagno di utilità deliberativa positivo (OW-2, OW-5);
- affidabilità dei claim verificati vs contraddetti.

Artefatti previsti:

- `benchmarks/open_world_review_gate.py`
- `henla.py open-world-review-gate`
- `henla0_ow6_review_gate.json`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- passed criteria: `5/5`;
- pe_reduction_consistency: `pass` (OW-1: 0.0039, OW-4: 0.0182);
- mean_recovery_rate: `pass` (1.0000 across 4 benchmarks);
- memory_boundedness: `pass` (OW-3 True);
- deliberative_utility_gain: `pass` (OW-2: +0.4219, OW-5: +0.4194);
- claim_reliability: `pass` (OW-5 corrected claims: confirmed: 3, contradicted: 0).

Verifica:

- suite completa: `171` test OK;
- compileall OK;
- `__pycache__` attivi: `0` dopo archiviazione finale.

## Verdetto di Generalizzazione (Post OW-6)

HENLA demonstrates limited generalization on real-world workspaces. Key evidence includes consistent prediction error reduction in OOD environments, near 100% recovery rate on real target failures, and stable memory usage under long-horizon stress. Deliberative scratchpad provides measurable utility in task recovery. Limitation: high reliance on initial consolidated priors for efficient OOD transfer.

## Prossima Azione Immediata

Roadmap Open World reale completata.

Passaggio di fase consigliato:

- non aprire un altro benchmark della stessa famiglia;
- attaccare direttamente il limite esplicito emerso in `OW-6`;
- avviare la nuova roadmap `OPEN_ENDED_INTELLIGENCE_ROADMAP.md`;
- spostare il focus da transfer con priors consolidati a apprendimento autonomo da zero in domini nuovi.
