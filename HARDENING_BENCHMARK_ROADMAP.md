# HENLA Hardening Benchmark Roadmap

Stato generale: `Done`

Obiettivo:
Passare da readiness architetturale a validazione ecologica progressiva. Da questo punto non si aggiungono moduli cognitivi senza una prova che mostri stabilita, costo, regressioni e limiti in ambienti piu lunghi, variabili e meno sintetici.

Stato di partenza:

```text
HENLA-0 -> HENLA-10: Done
Post-Roadmap Recursive Cognitive Scaling: Done
Research track PR-17 / PR-10 / PR-16 / PR-14: Done base
PR-18 Large Scale Readiness Gate: Done
Readiness finale: ready
Suite locale finale PR-18: 138 test OK
```

## Principio

La fase hardening misura cosa resta vero quando HENLA viene esposta a run piu lunghi, rumore controllato, fallimenti ripetuti, trasferimento tra ambienti, memoria crescente e merge distribuiti.

Regola:

```text
feature complete non basta;
serve survival evidence.
```

## HB-1 Long Nursery Run

Stato: `Done`

Obiettivo:
Far girare HENLA a lungo in ambiente protetto, misurando se memoria, pruning, attention, subgraphs, micro-pattern, scratchpad e readiness restano stabili.

Metriche:

- prediction_error trend;
- viability trend;
- memory pressure;
- edge decayed/archived;
- pattern migrati;
- scratchpad usefulness;
- attention stability;
- principle stability;
- recursive micro-pattern growth;
- readiness score nel tempo.

Artefatti previsti:

- `benchmarks/hardening_long_nursery.py`
- `henla0_hb1_long_nursery.json`
- `henla.py hardening-nursery`
- `tests/test_henla0.py`

Exit criteria:

- run completa senza eccezioni;
- prediction error finale non peggiora rispetto alla prima finestra;
- viability finale non collassa sotto la viability iniziale;
- memory pressure resta sotto soglia;
- almeno uno snapshot mostra pattern/memoria consolidata;
- nessun `__pycache__` attivo resta fuori archivio dopo verifica.

Risultato attivo:

- status: `passed`;
- steps: `120`;
- episode count: `120`;
- prediction error stable: `true`;
- first window mean prediction error: `0.0759`;
- final window mean prediction error: `0.0770`;
- viability stable: `true`;
- first viability: `0.7899`;
- final viability: `0.7100`;
- memory bounded: `true`;
- compressed pressure: `0.0833`;
- scratchpad useful: `true`;
- base micro-patterns: `3`;
- recursive micro-patterns: `2`;
- pruning decayed/archived: `0/0`.

Nota di hardening:

Il primo run HB-1 ha fallito per crescita del prediction error. La causa era una calibrazione errata: `HyperGraph.predict_valence_for_action()` usava `edge.weight` come proxy diretto della valenza attesa. Nei run lunghi il peso cresceva verso valori alti, rendendo HENLA troppo ottimista. Correzione applicata: il weight resta forza dell'evidenza, mentre la valenza attesa usa predictive gain firmato e bounded.

Verifica:

- suite completa: `141` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-2 Kindergarten Chaos Workspace

Stato: `Done`

Obiettivo:
Ambiente con file che cambiano, failure ricorrenti, recovery possibili e cause non sempre immediate.

Artefatti:

- `benchmarks/hardening_kindergarten.py`
- `henla0_hb2_kindergarten_chaos.json`
- `henla.py hardening-kindergarten`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- steps: `90`;
- episode count: `108`;
- mutations: `34`;
- failures: `18`;
- recovery rate: `1.0000`;
- final mean prediction error: `0.1604`;
- viability floor passed: `true`;
- memory bounded: `true`;
- compressed pressure: `0.2167`;
- loop bounded: `true`;
- base micro-patterns: `8`;
- recursive micro-patterns: `5`;
- pruning decayed/archived: `0/0`.

Verifica:

- suite completa: `143` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-3 Multi-Domain School Environment

Stato: `Done`

Obiettivo:
Combinare filesystem, testi, claim contraddittori, sequenze, documenti e task multi-step.

Artefatti:

- `benchmarks/hardening_school.py`
- `henla0_hb3_multi_domain_school.json`
- `henla.py hardening-school`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- cycles: `12`;
- episode count: `86`;
- failures: `14`;
- recovery rate: `1.0000`;
- final mean prediction error: `0.1253`;
- final viability: `0.7100`;
- claim count: `3`;
- reading verification: `1 confirmed`, `1 contradicted`, `1 unverified`;
- memory bounded: `true`;
- compressed pressure: `0.2167`;
- base micro-patterns: `8`;
- recursive micro-patterns: `5`;
- pruning decayed/archived: `0/0`.

Nota di hardening:

Il primo tentativo HB-3 ha usato il claim generico `read_chunk produces failure`, ma l'esperienza reale conteneva sia successi sia fallimenti di `read_chunk`, creando refutazione ambigua. La prova e stata resa piu pulita usando `hash_file produces failure`, che contraddice esperienza positiva stabile su `hash_file`.

Verifica:

- suite completa: `145` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-4 Open World Dry Run

Stato: `Done`

Obiettivo:
Run aperta ma ancora sandboxata, con novita alta e limiti espliciti di sicurezza.

Artefatti:

- `benchmarks/hardening_open_world.py`
- `henla0_hb4_open_world_dry_run.json`
- `henla.py hardening-open-world`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- steps: `80`;
- episode count: `90`;
- created targets: `34`;
- unique targets: `33`;
- novelty coverage: `21`;
- blocked unsafe targets: `10`;
- failures: `10`;
- recovery rate: `1.0000`;
- final mean prediction error: `0.0827`;
- final viability: `0.7100`;
- memory bounded: `true`;
- bounded exploration: `true`;
- loop events: `0`;
- compressed pressure: `0.2000`;
- base micro-patterns: `7`;
- recursive micro-patterns: `5`;
- pruning decayed/archived: `0/0`.

Nota di hardening:

Il primo run completo HB-4 ha fallito per bounded exploration: la novelty cresceva oltre soglia. E stato aggiunto un `novelty_budget` esplicito; quando il budget e pieno, HENLA ripiega su osservazione (`list_dir`) invece di continuare ad ampliare il mondo. La metrica distingue ora target novel da target stabili e input testuali.

Verifica:

- suite completa: `147` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-5 Ablation Tests

Stato: `Done`

Obiettivo:
Misurare degradazione rimuovendo scratchpad, attention, pruning, analogy, principles e distributed packets.

Artefatti:

- `benchmarks/hardening_ablation.py`
- `henla0_hb5_ablation_tests.json`
- `henla.py hardening-ablation`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- passed modules: `6/6`;
- scratchpad: `decision gain > 0`, `net valence gain > 0`;
- attention: `retrieval cost increase > 0`, `relevance dilution > 0`;
- pruning: `noise reduction loss > 0`, critical pattern preserved;
- analogy: `candidate loss > 0`;
- principles: `accepted loss > 0`;
- distributed: `merged loss > 0`, remote shareable loss > 0.

Verifica:

- suite completa: `149` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-6 Failure Injection

Stato: `Done`

Obiettivo:
Iniettare errori, file mancanti, claim falsi, rumore e loop operativi per verificare recovery.

Artefatti:

- `benchmarks/hardening_failure_injection.py`
- `henla0_hb6_failure_injection.json`
- `henla.py hardening-failure-injection`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- failures: `4`;
- recovery rate: `1.0000`;
- negative edges: `3`;
- loop events: `1`;
- reading verification: `1 confirmed`, `2 contradicted`, `1 unverified`;
- false claims resisted: `true`;
- noise success rate: `1.0000`;
- selector prefers recovery: `true`;
- final mean prediction error: `0.1602`;
- final viability: `0.7578`;
- compressed pressure: `0.1333`.

Verifica:

- suite completa: `151` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-7 Transfer Evaluation

Stato: `Done`

Obiettivo:
Allenare su workspace A/B/C e misurare transfer su workspace D mai visto.

Artefatti:

- `benchmarks/hardening_transfer.py`
- `henla0_hb7_transfer_evaluation.json`
- `henla.py hardening-transfer`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- source workspaces: `3`;
- imported structures: `48`;
- transferred priors: `3`;
- source diversity: `3`;
- baseline mean prediction error: `0.0742`;
- transfer mean prediction error: `0.0468`;
- prediction error reduction: `0.0274`;
- baseline mean valence: `0.2795`;
- transfer mean valence: `0.2866`;
- valence gain: `0.0071`;
- local verification ok: `true`.

Verifica:

- suite completa: `153` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-8 Memory Growth Stress Test

Stato: `Done`

Obiettivo:
Stressare crescita memoria, pruning, compressione, retrieval e recursive micro-pattern.

Artefatti:

- `benchmarks/hardening_memory_growth.py`
- `henla0_hb8_memory_growth_stress.json`
- `henla.py hardening-memory-growth`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- episodes: `287`;
- failures: `31`;
- recovery rate: `1.0000`;
- transient targets: `16`;
- compressed patterns: `8`;
- compression ratio: `0.0279`;
- retrieval growth ratio: `0.01104585`;
- final graph edge ratio: `0.1777`;
- compression trend improves: `true`;
- graph ratio improves: `true`;
- recursive micro: `7` base, `4` recursive;
- compressed pressure: `0.1833`;
- reduced noise count: `12`;
- final mean prediction error: `0.1146`;
- final viability: `0.7100`.

Verifica:

- suite completa: `155` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-9 Distributed Merge Stress Test

Stato: `Done`

Obiettivo:
Merge di piu istanze indipendenti con pattern compatibili, conflittuali e rumorosi.

Artefatti:

- `benchmarks/hardening_distributed_merge.py`
- `henla0_hb9_distributed_merge_stress.json`
- `henla.py hardening-distributed-merge`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- remote packets: `4`;
- local shareable total: `17`;
- merged total: `38`;
- kept separate total: `3`;
- raw fields rejected: `raw_episodes`, `operational_noise`, `raw_scratchpads`;
- compatible support max: `2`;
- conflict retained count: `3`;
- duplicate growth bounded: `true`;
- local verification rule preserved: `true`;
- final unique total: `24`.

Verifica:

- suite completa: `157` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## HB-10 HENLA Release Candidate

Stato: `Done`

Obiettivo:
Congelare artefatti, report, CLI e benchmark minimi per una release candidate riproducibile.

Artefatti:

- `benchmarks/hardening_release_candidate.py`
- `henla0_hb10_release_candidate.json`
- `henla0_release_candidate_manifest.json`
- `henla.py hardening-release-candidate`
- `tests/test_henla0.py`

Risultato attivo:

- status: `passed`;
- release candidate id: `henla0-rc-2026-05-07`;
- benchmark gates: `16/16`;
- CLI smoke: `20/20`;
- frozen artifacts: `52`;
- recursive micro gate: `true`;
- missing artifacts: `0`.

Verifica:

- suite completa: `159` test OK;
- compileall OK;
- `__pycache__` attivi: `0`.

## Prossima Azione Immediata

Roadmap hardening completata. Prossimo passo: scegliere tra packaging/release del candidate congelato oppure nuova roadmap su ambienti Open World reali e meno sintetici.
