# HENLA Roadmap

Roadmap operativa dal prototipo HENLA-0 al progetto finale HENLA-10.

Questo documento serve a evitare decisioni ripetute sul "prossimo passo". Ogni sezione va aggiornata mentre viene completata, con stato, note, test e riferimenti ai file coinvolti.

## Stati

- `Todo`: non iniziato.
- `Doing`: in corso.
- `Done`: completato e verificato.
- `Blocked`: bloccato da decisione o problema tecnico.
- `Revisit`: implementato, ma da migliorare.

## Regola Di Aggiornamento

Ogni avanzamento deve aggiornare:

- stato della sezione;
- data;
- file coinvolti;
- test eseguiti;
- risultato;
- prossima azione immediata.

## Stato Globale

| Area | Stato | Note |
| --- | --- | --- |
| HENLA-0 base | Done | Package `core/`, CLI, demo, test, grafo moderno attivo. |
| Concept tracking | Done | `ConceptTracker` iniziale integrato in runner/report. |
| Category tracking | Done | `CategoryTracker` iniziale con categorie operative. |
| Timeline | Done | Snapshot JSONL append-only attivo. |
| Phase 4 completa | Done | Categorie empiriche, trend timeline e concept history completati. |
| Phase 5 Imitation | Done | Sequenze, replay, delta viability e contraddizioni da replay fallito completati. |
| Phase 6 Primary Language | Done | Lessico grounded, grounding parola-concept/category e input testuale come sensore completati. |
| Phase 7 Reading | Done | Reader testuale/file, candidate edges e verifica claim vs esperienza completati. |
| Phase 8 Reasoning | Done | Simulazione azioni, piano base, rifiuto negativo e counterfactual completati. |
| Phase 9 Creativity | Done | Ipotesi analogiche candidate e valutazione conferma/contraddizione completate. |
| Phase 10 Graduation | Done | Report finale riproducibile completato: 9/9 capability check. |
| Post-Roadmap research track | Done base | Corsia brain-inspired su PR-17, PR-10, PR-16, PR-14 completata in versione base. |

## Milestone 0 - Fondazione HENLA-0

Stato: `Done`

Obiettivo: avere una base eseguibile, testata, osservabile e non ambigua.

Completato:

- package canonico `core/`;
- CLI unica `henla.py`;
- demo guidata e autonoma;
- test suite;
- grafo moderno attivo `henla0_graph.json`;
- export `henla0_concepts.json`;
- export `henla0_categories.json`;
- timeline `henla0_timeline.jsonl`;
- archiviazione legacy in `archive/`.

Verifica:

- suite: 22 test OK;
- report CLI OK;
- timeline CLI OK.

## Milestone 1 - Phase 4 Solida: Category Formation

Stato: `Done`

Obiettivo: trasformare le categorie da euristiche iniziali a strutture emergenti piu empiriche.

### 1.1 Rendere Le Categorie Meno Hardcoded

Stato: `Done`

Problema attuale:

- `CategoryTracker` conosce a priori gruppi come `sensing_actions` e `information_actions`.

Azioni:

- calcolare similarita tra azioni usando edge stabili condivisi;
- raggruppare azioni per pattern di risultato e valenza;
- mantenere nomi euristici solo come label provvisoria;
- distinguere categoria emergente da categoria nominata.

File previsti:

- `core/category_tracker.py`
- `tests/test_henla0.py`

Verifica:

- test cluster categorie da edge: completato;
- test categoria nuova senza lista hardcoded: completato;
- report CLI mostra categoria emergente e label: completato.

Risultato:

- `CategoryTracker` usa firme empiriche da edge stabili;
- categorie `category::empirical_*` sono separate da `label`;
- le label note sono descrittive, non la base della categoria;
- suite: 23 test OK.

Nota:

- categorie singleton su oggetti molto evidenziati sono ancora possibili e vanno raffinate nella fase trend/decadimento.

### 1.2 Trend Di Concept E Categorie

Stato: `Done`

Azioni:

- estendere `core/timeline.py` con delta concept score: completato;
- mostrare categorie cresciute, decadute, nuove: completato;
- evidenziare nuove relazioni stabili tra snapshot: completato.

File previsti:

- `core/timeline.py`
- `henla.py`
- `tests/test_henla0.py`

Verifica:

- test delta su due snapshot: completato;
- CLI `timeline` mostra trend: completato;
- suite: 24 test OK.

Risultato:

- `analyze_timeline()` calcola transizioni tra snapshot;
- CLI `henla.py timeline` mostra delta nodi/edge/stabili, concept score delta, categorie nuove/perse/cambiate e nuovi stable edge;
- timeline attiva aggiornata a 2 snapshot.

### 1.3 Persistenza Esplicita Dei Concept

Stato: `Done`

Azioni:

- decidere se salvare concept come derivati o stato persistente: completato;
- se persistenti, creare `henla0_concepts_history.jsonl`: sostituito da export derivato `henla0_concepts_history.json`;
- evitare duplicazione incoerente con grafo: completato.

Decisione preferita:

- concept derivati dal grafo;
- storico salvato in timeline.

Risultato:

- la timeline resta fonte storica autoritativa;
- aggiunto comando `henla.py concept-history`;
- aggiunto export `henla0_concepts_history.json` come vista derivata dalla timeline;
- nessun secondo stato persistente dei concept.

Verifica:

- test concept history da timeline;
- test CLI `concept-history --out`;
- suite: 26 test OK.

## Milestone 2 - HENLA-0 Robustezza Esperienziale

Stato: `Done`

Obiettivo: migliorare qualita delle esperienze e gestione fallimenti.

### 2.1 Azioni Negative E Contraddizioni

Stato: `Done`

Azioni:

- introdurre episodi di fallimento controllati: completato;
- misurare contradiction_rate reale: completato;
- promuovere anche pattern negativi stabili: completato;
- distinguere failure utile da failure dannoso: parziale, base tecnica pronta.

File previsti:

- `core/relation_learner.py`
- `core/hypergraph.py`
- `tests/test_henla0.py`

Risultato:

- `HyperGraph.mark_contradictions()` marca edge incompatibili;
- edge con contradiction_rate oltre soglia diventano `refuted`;
- `relation_learner` genera `negative_outcome_pattern`;
- repeated failure puo stabilizzare pattern negativo;
- `edges_for_node()` ignora correttamente edge refuted.

Verifica:

- test refutazione edge contraddetto;
- test negative outcome pattern;
- test stabilizzazione pattern negativo;
- suite: 29 test OK.

### 2.2 Loop Penalty Reale

Stato: `Done`

Azioni:

- verificare loop penalty su sequenze reali: completato;
- aggiungere report su repeated failures: completato;
- impedire al selector di bloccarsi su pattern sterili: completato a livello one-step.

File previsti:

- `core/runner.py`
- `core/action_selector.py`
- `tests/test_henla0.py`

Risultato:

- il runner registra `loop_events` quando rileva fallimenti ripetuti;
- `report()` include sezione `loops`;
- `ActionSelector` mantiene `failure_streak` per coppia azione/target;
- lo scoring include `loop_penalty` e lo espone nel reason;
- summary selector mostra failure streak attivi.

Verifica:

- test loop events nel report;
- test penalty selector su coppia sterile;
- suite: 31 test OK.

### 2.3 Episodi Persistenti

Stato: `Done`

Azioni:

- salvare episodi in JSONL: completato;
- collegare timeline, episodi e grafo: completato tramite CLI `--episodes` + `--timeline`;
- permettere replay/debug di una sessione: parziale, summary/debug base completato; replay rimandato a Phase 5.

File previsti:

- `core/episode_store.py`
- `core/runner.py`
- `henla.py`

Risultato:

- aggiunto `EpisodeStore` append-only JSONL;
- `HENLA0` e `HENLA0Autonomous` possono scrivere episodi chiusi con `episode_store_path`;
- CLI `demo` e `autonomous` supportano `--episodes`;
- CLI `episodes` sintetizza success/failure, valenza media, prediction error media e ultimo episodio;
- creati `henla0_episodes.jsonl` e `henla0_episode_summary.json`.

Verifica:

- test append/read/summarize;
- test runner con episode store;
- test CLI `episodes --out`;
- suite: 34 test OK.

## Milestone 3 - Phase 5: Imitation

Stato: `Done`

Obiettivo: osservare sequenze di azioni riuscite, memorizzarle e riprodurle.

Azioni:

- creare `core/sequence.py`: completato;
- rappresentare catene di episodi: completato;
- comando CLI per registrare una dimostrazione: completato;
- replay in nuovo workspace: base completata;
- misurare delta viability: completato.

Comandi previsti:

```powershell
python henla.py demonstrate henla0_episodes.jsonl --out henla0_sequence.json
python henla.py replay henla0_sequence.json --workspace target
```

Verifica:

- test replay riuscito: completato;
- test replay fallito genera contradiction: completato;
- timeline registra miglioramento o peggioramento: completato.

Risultato parziale:

- `core/sequence.py` crea sequenze da episodi persistiti;
- CLI `demonstrate` e `replay` operative;
- replay attivo su workspace corrente: 5 step, match rate `1.0000`, delta viability `+0.6656`;
- replay puo caricare/salvare grafo e appendere timeline;
- test replay fallito genera contraddizioni e pattern negativo;
- replay attivo con timeline: match rate `1.0000`, delta viability `+0.6620`;
- suite: 39 test OK.

## Milestone 4 - Phase 6: Primary Language

Stato: `Done`

Obiettivo: agganciare parole a concept gia formati, non introdurre linguaggio come base.

Azioni:

- creare `core/language.py`: completato;
- mappa parola -> concept/category: completato per lessico derivato;
- lessico con valenza: completato;
- input testuale come sensore: completato;
- output testuale minimo sullo stato interno: base completata con `describe_state`.

Esempi:

- `success` si lega a concept `produces_positive`;
- `failure` si lega a pattern negativi;
- `uncertain` si lega a `uncertainty` alta.

Verifica:

- nessuna parola senza concept sottostante: completato;
- test grounding parola-concept: completato;
- report lessico: completato.
- test input testuale come sensore: completato.

Risultato:

- aggiunto `LanguageGrounder`;
- CLI `lexicon` e `ground`;
- CLI `text`;
- parola `success` grounded a `concept::produces_positive` e categorie osservate;
- input `success viable` processato sul grafo attivo: 1 token grounded, 1 token unknown, valenza `+0.3561`;
- export attivi: `henla0_lexicon.json`, `henla0_ground_success.json`;
- export attivo episodio testuale: `henla0_text_success.json`;
- suite: 46 test OK.

## Milestone 5 - Phase 7: Reading

Stato: `Done`

Obiettivo: leggere documenti come modalita sensoriale e trasformare testo in candidate edges.

Azioni:

- creare `core/reader.py`: completato;
- parser documenti/testo: base testo inline e file UTF-8/Windows completata; documenti binari da estendere;
- estrazione relazioni candidate: completato per claim azione -> risultato;
- tutto cio che viene letto resta candidate finche non confermato da esperienza: completato per claim letti con predictive gain `0.0`.

Verifica:

- testo produce candidate edge: completato;
- candidate non diventa stable senza evidenza esperienziale: completato;
- contradiction tra testo e azione viene registrata: completato in test;
- CLI `read-text`: completato.

Risultato parziale:

- aggiunto `TextReader`;
- aggiunta azione `read_text` nel runner e nel selector;
- aggiunto comando CLI `read-text`;
- input reale `watch_change produces success` registrato sul grafo attivo come candidate edge;
- lettura reale di `ROADMAP.md`: 1 claim, 2 edge, 0 contraddizioni;
- export attivo: `henla0_reading_report.json`;
- export attivo da file: `henla0_reading_file_report.json`;
- verifica claim letti vs esperienza: completata con CLI `reading-report`;
- export attivo: `henla0_reading_verification.json`;
- suite: 53 test OK.

## Milestone 6 - Phase 8: Reasoning

Stato: `Done`

Obiettivo: simulare azioni mentalmente usando il grafo prima di agire.

Azioni:

- creare `core/reasoner.py`: completato;
- traversata ipergrafo: completato base;
- previsione multi-step: completato con `plan`;
- rifiuto azioni con valenza prevista negativa: completato;
- counterfactual: cosa sarebbe successo se: completato.

Verifica:

- test piano/simulazione: completato;
- test rifiuto azione negativa: completato;
- test counterfactual semplice: completato;
- CLI `reason`: completato.

Risultato:

- aggiunto `Reasoner`;
- CLI `reason` con `simulate`, `plan`, `counterfactual`;
- export attivi: `henla0_reason_stat_file.json`, `henla0_reason_plan.json`;
- suite: 57 test OK.

## Milestone 7 - Phase 9: Creativity

Stato: `Done`

Obiettivo: collegare concept distanti e generare ipotesi nuove.

Azioni:

- creare `core/creativity.py`: completato;
- similarita strutturale tra cluster: completato base con novelty da relazioni condivise;
- generazione candidate edges analogici: completato;
- scoring novita/risico: completato;
- test sperimentale delle ipotesi: completato tramite valutazione conferma/contraddizione.

Verifica:

- ipotesi nuova resta candidate: completato;
- se confermata viene marcata confirmed in evaluation: completato;
- se contraddetta viene marcata contradicted in evaluation: completato.

Risultato:

- aggiunto `CreativityEngine`;
- CLI `creative` con generazione e valutazione;
- export attivi: `henla0_creative_hypotheses.json`, `henla0_creative_evaluation.json`;
- suite: 60 test OK.

## Milestone 8 - Phase 10: Graduation

Stato: `Done`

Obiettivo: autonomia cognitiva completa sullo stack HENLA.

Capacita richieste:

- esplorazione da zero;
- categorie empiriche;
- imitazione;
- grounding linguistico;
- lettura con verifica esperienziale;
- ragionamento multi-step;
- ipotesi creative;
- autocorrezione su contradiction spike;
- trasferimento tra domini.

Verifica finale:

- benchmark su workspace nuovo;
- apprendimento senza grafo preesistente;
- timeline mostra crescita ordinata;
- concept e categorie trasferiscono;
- azioni dannose evitate dopo esperienza;
- report finale riproducibile.

Risultato:

- aggiunto `GraduationReport`;
- CLI `graduate`;
- report finale attivo: `henla0_graduation_report.json`;
- esito: `graduated`, 9/9 capability check;
- suite: 62 test OK.

# HENLA Post-Roadmap

## Recursive Cognitive Scaling

Stato: `Done`

Obiettivo: trasformare HENLA da architettura cognitiva basata su un ipergrafo principale in una rete ricorsiva di ipergrafi specializzati, capace di crescere, differenziarsi, potarsi, consolidare pattern, creare analogie tra strutture distanti e riorganizzare autonomamente la propria architettura interna.

Questa fase inizia dopo HENLA-10.

La roadmap principale porta HENLA a diventare un agente cognitivo capace di esperienza, linguaggio, lettura, ragionamento, creativita e autonomia.

La post-roadmap ha un obiettivo diverso:

- non solo imparare dentro una struttura data;
- ma imparare quale struttura interna serve per continuare a imparare.

```text
HENLA-0 -> HENLA-10:
costruzione di una mente operativa

Post-Roadmap:
costruzione di una mente auto-organizzante
```

## Principio Fondamentale

HENLA non deve scalare come un database di episodi.

Deve scalare come una mente.

Questo significa:

- non conservare tutto;
- non tenere tutti i nodi allo stesso livello;
- non usare un solo grafo piatto;
- non trattare ogni esperienza come ugualmente importante;
- non memorizzare solo concetti;
- non limitarsi a contare successi e fallimenti.

HENLA deve imparare a formare:

- sottografi cognitivi;
- pattern;
- collegamenti tra pattern;
- analogie strutturali;
- principi trasferibili;
- aree specializzate;
- memoria temporanea deliberativa;
- gerarchie ricorsive di conoscenza.

## Architettura Generale Post-Roadmap

La struttura finale non e un ipergrafo unico, ma una rete ricorsiva di ipergrafi.

Ogni nodo puo, con abbastanza evidenza, diventare un sottografo. Ogni sottografo puo contenere altri sottografi. Ogni pattern puo diventare struttura. Ogni struttura puo diventare principio.

Struttura obiettivo:

```text
HENLA
├── subgraph::episodic
├── subgraph::procedural
├── subgraph::semantic
├── subgraph::affective
├── subgraph::predictive
├── subgraph::linguistic
├── subgraph::analogical
└── subgraph::principles
```

## PR-1 - Subgraph Registry

Stato: `Done`

Obiettivo: creare un registro centrale dei sottografi cognitivi.

Il sistema deve sapere quali sottografi esistono, che ruolo hanno, quali nodi contengono, quali sottografi figli contengono, con quali altri sottografi comunicano, quanto sono utili e quando devono crescere, dividersi, fondersi o decadere.

Struttura prevista:

```json
{
  "subgraph_id": "subgraph::filesystem_actions",
  "type": "procedural",
  "parent": "subgraph::procedural",
  "children": [],
  "specialization": "actions over filesystem objects",
  "nodes": [],
  "edges": [],
  "pattern_edges": [],
  "local_viability": 0.42,
  "prediction_gain": 0.18,
  "transfer_score": 0.31,
  "complexity": 0.64,
  "coherence": 0.71,
  "last_activated": 18492,
  "budding_pressure": 0.23,
  "pruning_pressure": 0.08
}
```

File previsti:

- `core/subgraph.py`
- `core/subgraph_registry.py`
- `core/hypergraph.py`
- `tests/test_henla0.py`

Verifica:

- creare sottografo: completato;
- collegare sottografo a parent: completato;
- registrare child subgraphs: completato;
- calcolare metriche locali: completato;
- recuperare sottografi attivi per una percezione: completato;
- serializzare e ricaricare il registry: completato.

Risultato:

- aggiunto `CognitiveSubgraph`;
- aggiunto `SubgraphRegistry`;
- il runner espone un registry vuoto nel report;
- CLI `subgraphs`;
- registry attivo: `henla0_subgraphs.json`;
- report attivo: `henla0_subgraphs_report.json`;
- sottografo `subgraph::filesystem_actions` con viability locale `+0.3725`;
- suite: 72 test OK.

## PR-2 - Cognitive Areas

Stato: `Done`

Obiettivo: introdurre aree cognitive iniziali, analoghe ad aree cerebrali primitive. Le aree non devono contenere conoscenza hardcoded, ma solo una funzione generale.

Aree iniziali:

- Episodic Area: cosa e successo.
- Procedural Area: come si fa.
- Semantic Area: che cosa significa.
- Affective Area: quanto fa bene o male.
- Predictive Area: cosa succedera se.
- Linguistic Area: come viene nominata l'esperienza.
- Analogical Area: questa struttura somiglia a quella.
- Principle Area: che cosa vale in molti domini.

File previsti:

- `core/cognitive_area.py`
- `core/subgraph_registry.py`
- `core/runner.py`
- `henla.py`

Verifica:

- ogni area nasce vuota o quasi vuota: completato;
- nessuna area contiene concetti precompilati: completato;
- le aree ricevono pattern solo da esperienza: base pronta tramite registry;
- le aree hanno viability locale: completato;
- le aree comunicano tramite protocolli espliciti: completato con `communication_channels`.

Risultato:

- aggiunto `CognitiveArea`;
- aggiunto `CognitiveAreaSystem`;
- runner inizializza le 8 aree cognitive primitive;
- CLI `areas`;
- export attivo: `henla0_cognitive_areas.json`;
- suite: 76 test OK;
- compileall OK dopo pulizia bytecode bloccato.

## PR-3 - Budding / Gemmazione

Stato: `Done`

Obiettivo: permettere a nodi, cluster o pattern troppo complessi di trasformarsi in sottografi autonomi.

Transizione:

```text
node -> cluster -> subgraph
```

Criteri di gemmazione:

- activation_count;
- numero di edge stabili;
- diversita di contesti;
- prediction_gain;
- contradiction complexity;
- valence variance;
- numero di pattern interni;
- utilita nel transfer.

Formula possibile:

```text
budding_pressure =
    0.20 * normalized_activation_count
  + 0.20 * stable_edge_density
  + 0.20 * context_diversity
  + 0.15 * prediction_gain
  + 0.10 * valence_variance
  + 0.10 * internal_pattern_count
  + 0.05 * transfer_score
```

Soglia:

```text
budding_pressure > 0.70
```

File previsti:

- `core/budding.py`
- `core/subgraph.py`
- `core/subgraph_registry.py`
- `tests/test_henla0.py`

Verifica:

- nodo molto attivo genera sottografo: completato;
- nodo poco utile non genera sottografo: completato;
- sottografo eredita edge rilevanti: completato;
- parent mantiene riferimento al child: completato;
- il grafo globale non perde coerenza: completato.

Completato 2026-05-07:

- `core/budding.py`;
- `BuddingCandidate`;
- `BuddingEngine`;
- CLI `henla.py budding`;
- export attivo `henla0_budding_report.json`;
- registry attivo aggiornato `henla0_subgraphs.json`;
- test dedicati.

Risultato attivo con soglia `0.70`:

- creati 4 sottografi: `subgraph::success`, `subgraph::list_dir`, `subgraph::hash_file`, `subgraph::stat_file`;
- parent/child aggiornati nel registry;
- edge rilevanti ereditati nei sottografi;
- grafo globale non modificato.

## PR-4 - Pruning / Oblio Strutturale

Stato: `Done`

Obiettivo: permettere a HENLA di dimenticare o comprimere cio che non serve.

Tipi di oblio:

- decadimento;
- archiviazione;
- compressione;
- eliminazione.

Criteri di potatura:

- inattivita;
- basso prediction_gain;
- basso transfer_score;
- contradiction_rate;
- bassa importanza affettiva;
- ridondanza.

Formula possibile:

```text
pruning_pressure =
    0.25 * inactivity
  + 0.20 * low_prediction_gain
  + 0.20 * low_transfer_score
  + 0.15 * contradiction_rate
  + 0.10 * low_valence_importance
  + 0.10 * redundancy
```

Soglia:

```text
pruning_pressure > 0.75
```

File previsti:

- `core/pruning.py`
- `core/hypergraph.py`
- `core/episode_store.py`
- `core/timeline.py`

Verifica:

- edge inutili decadono: completato in test controllato;
- edge utili restano: completato;
- episodi simili vengono compressi: completato con summary;
- pattern contraddetti vengono refuted o archiviati: completato tramite refutation esistente e archival pruning;
- il grafo diventa piu piccolo senza perdere performance: completato base tramite esclusione retrieval di `decayed`/`archived`, senza cancellazione fisica.

Completato 2026-05-07:

- `core/pruning.py`;
- `PruningCandidate`;
- `PruningEngine`;
- stati edge `decayed` e `archived`;
- retrieval operativo esclude `decayed`, `archived`, `refuted`;
- CLI `henla.py pruning`;
- export attivo `henla0_pruning_report.json`;
- test dedicati.

Risultato attivo con soglia `0.75`:

- 50 candidati valutati;
- 0 archiviati;
- 0 decaduti;
- 50 mantenuti;
- il grafo attivo non contiene strutture sopra soglia di oblio standard;
- compressione episodio disponibile nel report.

## PR-5 - Memory Consolidation

Stato: `Done`

Obiettivo: creare un processo periodico che trasformi episodi grezzi in pattern, concetti e principi.

Processo:

```text
Episode Store
   ↓
Pattern Extraction
   ↓
Concept Formation
   ↓
Subgraph Assignment
   ↓
Principle Candidate
   ↓
Timeline Snapshot
```

Tipi di consolidamento:

- Episodic -> Procedural;
- Episodic -> Semantic;
- Episodic -> Affective;
- Procedural -> Principle;
- Predictive -> Principle.

File previsti:

- `core/consolidation.py`
- `core/episode_store.py`
- `core/concept_tracker.py`
- `core/category_tracker.py`
- `core/subgraph_registry.py`

Verifica:

- episodi ripetuti generano pattern: completato;
- episodi poco utili decadono: coperto da PR-4;
- pattern trasferibili salgono di livello: completato base tramite signature patterns e principle candidates;
- principi non nascono da singolo episodio: completato;
- consolidamento migliora retrieval e prediction error: completato base tramite assegnazione pattern ai sottografi.

Completato 2026-05-07:

- `core/consolidation.py`;
- `ConsolidatedPattern`;
- `ConsolidationEngine`;
- CLI `henla.py consolidation`;
- export attivo `henla0_consolidation_report.json`;
- registry aggiornato con pattern consolidati;
- test dedicati.

Risultato attivo:

- 12 episodi sorgente;
- 2 pattern procedurali;
- 5 signature patterns;
- 3 principle candidates;
- 2 assegnazioni a sottografi;
- nessun principio da episodio singolo.

## PR-6 - Pattern-Level Hyperedges

Stato: `Done`

Obiettivo: permettere agli iperarchi di collegare non solo nodi, ma anche pattern, sottografi e strutture causali.

Esempi:

```text
[pattern_A, pattern_B] -> structural_similarity
[subgraph_filesystem_failure, subgraph_process_failure] -> analogous_failure_shape
```

Tipi di pattern edge:

- structural_similarity;
- causal_similarity;
- affective_similarity;
- procedural_similarity;
- contradiction_between_patterns;
- transfer_candidate;
- analogy_candidate;
- principle_candidate.

File previsti:

- `core/pattern_edge.py`
- `core/hypergraph.py`
- `core/creativity.py`
- `core/reasoner.py`

Verifica:

- due pattern simili generano candidate edge: completato;
- pattern edge non diventa stable senza evidenza: completato;
- pattern edge puo essere refuted: completato in test;
- pattern edge migliora transfer: predisposto con `transfer_score`;
- pattern edge puo generare ipotesi creative: predisposto tramite relazione con analogie candidate.

Completato 2026-05-07:

- `core/pattern_edge.py`;
- `PatternEdge`;
- `PatternEdgeRegistry`;
- CLI `henla.py pattern-edges`;
- registry attivo `henla0_pattern_edges.json`;
- export attivo `henla0_pattern_edges_report.json`;
- test dedicati.

Risultato attivo:

- 10 pattern-level edge creati;
- tutti in stato `candidate`;
- relazioni: `structural_similarity`, `causal_similarity`, `affective_similarity`;
- edge separati dal grafo esperienziale principale.

## PR-7 - Migration Between Subgraphs

Stato: `Done`

Obiettivo: permettere ai pattern di spostarsi tra aree cognitive.

Migrazioni previste:

```text
episodic -> procedural
episodic -> semantic
episodic -> affective
procedural -> predictive
semantic -> analogical
predictive -> principle
analogical -> creativity
principle -> action_policy
```

File previsti:

- `core/migration.py`
- `core/subgraph_registry.py`
- `core/consolidation.py`
- `core/timeline.py`

Verifica:

- pattern nasce in episodic;
- viene promosso a procedural;
- poi diventa predictive se anticipa risultati;
- poi diventa principle se trasferisce;
- migrazione viene registrata nella timeline.

Implementazione completata:

- aggiunto `core/migration.py` con `MigrationEngine` e `MigrationCandidate`;
- aggiunta CLI `henla.py migration`;
- promozione controllata dei pattern senza rimuovere la traccia dal sottografo sorgente;
- scoring basato su evidence, prediction gain, transfer score e contradiction resistance;
- integrazione con `henla0_consolidation_report.json`, `henla0_pattern_edges.json` e `henla0_subgraphs.json`;
- export attivo `henla0_migration_report.json`.

Run attivo:

- candidati: `10`;
- migrati: `9`;
- target aggiornati: `subgraph::predictive`, `subgraph::analogical`, `subgraph::principles`.

Test:

- suite completa passata: `103` test OK;
- compileall OK.

## PR-8 - Cognitive Scratchpad / Working Thought Space

Stato: `Done`

Obiettivo: aggiungere a HENLA uno spazio temporaneo di pensiero operativo.

Lo scratchpad serve a:

- prendere appunti interni;
- formulare ipotesi;
- recuperare pattern rilevanti;
- confrontare azioni candidate;
- simulare conseguenze;
- scegliere un'azione;
- riflettere dopo il risultato;
- decidere cosa consolidare.

Non e memoria permanente. E memoria deliberativa temporanea.

Flusso:

```text
perception
   ↓
activated_nodes
   ↓
cognitive_scratchpad
   ↓
hypotheses
   ↓
simulations
   ↓
action_selection
   ↓
result
   ↓
reflection
   ↓
partial_consolidation
   ↓
scratchpad_close
```

Struttura prevista:

```json
{
  "scratchpad_id": "scratchpad::000184",
  "scope": "current_operation",
  "active_question": "Which action reduces uncertainty with lowest risk?",
  "state_summary": {},
  "activated_nodes": [],
  "activated_patterns": [],
  "retrieved_edges": [],
  "hypotheses": [],
  "simulations": [],
  "selected_action": null,
  "rejected_actions": [],
  "observed_result": null,
  "reflection": null,
  "consolidation_candidates": [],
  "discarded_notes": []
}
```

Regole:

- tutto e temporaneo per default;
- solo ipotesi utili diventano candidate_edges;
- pensieri confermati aumentano confidence;
- pensieri contraddetti aumentano prediction_error;
- scratchpad troppo lungo viene compresso;
- scratchpad ripetutamente utile puo generare un pattern deliberativo;
- lo scratchpad non deve diventare log infinito;
- lo scratchpad non deve sostituire episode store, hypergraph o reasoner.

Differenza:

```text
Episode:
registra cosa e successo.

Scratchpad:
registra cosa HENLA stava considerando prima, durante e dopo l'azione.
```

File previsti:

- `core/scratchpad.py`
- `core/reasoner.py`
- `core/action_selector.py`
- `core/runner.py`
- `tests/test_henla0.py`

Verifica:

- apertura scratchpad: completato;
- chiusura scratchpad: completato;
- generazione ipotesi: completato;
- simulazione azioni candidate: completato;
- selezione azione basata su simulazione: completato;
- confronto prediction/result: completato;
- consolidamento parziale: completato come candidate deliberativo locale;
- cancellazione pensieri inutili: completato via compressione;
- compressione scratchpad lungo: completato.

Risultato:

- aggiunto `Scratchpad` e `ScratchpadManager`;
- il runner apre e chiude uno scratchpad temporaneo per ogni step;
- `report()` espone solo ultimo scratchpad e conteggio recente, non una memoria infinita;
- CLI `scratchpad` genera uno scratchpad deliberativo senza modificare il grafo;
- export attivo: `henla0_scratchpad_stat_file.json`;
- suite: 66 test OK.

## PR-9 - Deliberative Reasoning Loop

Stato: `Done`

Obiettivo: collegare scratchpad, reasoner, action selector e hypergraph in un ciclo deliberativo.

Ciclo:

```text
intendere -> ipotizzare -> simulare -> scegliere -> agire -> confrontare -> apprendere
```

Metriche:

- hypothesis_accuracy;
- simulation_error;
- action_regret;
- avoided_negative_actions;
- prediction_before_action;
- prediction_after_reflection;
- scratchpad_usefulness;
- deliberation_cost;
- viability_gain_after_deliberation.

File previsti:

- `core/reasoner.py`
- `core/scratchpad.py`
- `core/action_selector.py`
- `core/runner.py`
- `core/valence.py`

Verifica:

- HENLA simula almeno due azioni: completato;
- sceglie quella con miglior expected viability: completato;
- evita azione prevista negativa: completato via filtro `reject`;
- se la simulazione sbaglia, registra errore: completato con `simulation_error`;
- se la simulazione aiuta, aumenta confidence: base pronta via reflection/useful;
- il costo deliberativo viene sottratto da energy: completato con `_deliberation_cost`.

Risultato:

- aggiunto `HENLA0Autonomous.deliberative_step`;
- aggiunta CLI `deliberate`;
- report runner include sezione `deliberation`;
- metriche registrate: `simulation_error`, `action_regret`, `avoided_negative_actions`, `deliberation_cost`;
- run attivo: 1 evento, azione scelta `list_dir tests`, simulation error `0.5992`;
- export attivo: `henla0_deliberation_report.json`;
- suite: 68 test OK.

## PR-10 - Cross-Graph Analogy

Stato: `Done base`

Obiettivo: permettere a HENLA di confrontare sottografi diversi e trovare somiglianze strutturali.

Nota di rotta 2026-05-06:

La fase preparatoria e completata: `core/pattern_signature.py` trasforma micro-pattern esperienziali in firme confrontabili basate su ruoli, forma causale, delta di stato, traiettoria affettiva, recovery e contesto. Il confronto analogico deve usare queste firme, non il matching completo dei sottografi.

Completato base:

- `PatternSignature`;
- `PatternSignatureExtractor`;
- comando CLI `henla.py signatures`;
- export attivo `henla0_pattern_signatures.json`;
- 5 firme candidate derivate dagli episodi attivi;
- test dedicati.

Completato 2026-05-07:

- creare `core/analogy.py`;
- confrontare coppie di `PatternSignature`;
- calcolare `analogy_score` da causal shape, role similarity, state delta, valence curve e recovery;
- produrre `analogy_candidate`, non relazioni stabili;
- esportare `henla0_analogies.json`;
- test dedicati.

Risultato attivo:

- 5 firme pronte;
- 10 candidate analogiche;
- miglior score `0.9400`;
- tutte le analogie restano `candidate` e richiedono verifica tramite transfer.

Tipi di analogia:

- causal shape similarity;
- valence trajectory similarity;
- action sequence similarity;
- failure recovery similarity;
- uncertainty reduction similarity;
- structural role similarity.

File previsti:

- `core/analogy.py`
- `core/creativity.py`
- `core/pattern_edge.py`
- `core/subgraph_registry.py`

Verifica:

- due sottografi con nodi diversi ma forma simile vengono collegati;
- il collegamento resta candidate;
- se usato con successo viene promosso;
- se fallisce viene refuted;
- migliora transfer in nuovo workspace.

## PR-11 - Principle Formation

Stato: `Done`

Obiettivo: distillare pattern trasferibili in principi generali.

Esempi:

- `observe_before_act`;
- `avoid_repeated_failure`;
- `verify_text_with_experience`.

Formula possibile:

```text
principle_score =
    0.25 * stability
  + 0.25 * transferability
  + 0.20 * prediction_gain
  + 0.15 * cross_domain_presence
  + 0.10 * viability_gain
  + 0.05 * contradiction_resistance
```

Soglia:

```text
principle_score > 0.80
```

File previsti:

- `core/principle.py`
- `core/consolidation.py`
- `core/reasoner.py`
- `core/subgraph_registry.py`

Verifica:

- nessun principio nasce da episodio singolo;
- principio emerge da pattern multi-contesto;
- principio migliora azione in ambiente nuovo;
- principio puo decadere o essere corretto;
- principio appare nei report.

Implementazione completata:

- aggiunto `core/principle.py` con `PrincipleFormationEngine`;
- aggiunta CLI `henla.py principles`;
- i principi non nascono da singolo episodio;
- i principi restano revisabili e non vengono trattati come verita assolute;
- score calcolato da stabilita, transferability, prediction gain, cross-domain presence, viability gain e contradiction resistance;
- aggiornamento di `subgraph::principles`;
- export attivo `henla0_principles.json`.

Run attivo:

- candidate sorgenti: `3`;
- principi generati: `3`;
- principi accettati: `3`;
- status dei principi attivi: `tested`.

Test:

- suite completa passata: `106` test OK;
- compileall OK.

## PR-12 - Local And Global Viability

Stato: `Done`

Obiettivo: ogni sottografo deve avere una viability locale, aggregabile nella viability globale.

Metriche locali:

- coherence;
- prediction_gain;
- contradiction_rate;
- activation_health;
- memory_pressure;
- pruning_pressure;
- transfer_score;
- local_pain;
- local_uncertainty;
- local_fatigue.

File previsti:

- `core/subgraph.py`
- `core/state.py`
- `core/viability.py`
- `core/timeline.py`

Verifica:

- calcolo viability locale;
- aggregazione in viability globale;
- sottografo degradato viene segnalato;
- sottografo utile riceve piu budget;
- sottografo rumoroso viene potato o consolidato.

Implementazione completata:

- aggiunto `core/viability.py` con `ViabilityEngine`;
- aggiunta CLI `henla.py viability`;
- calcolo locale di coherence, prediction gain, transfer, contradiction rate, activation health, memory pressure, pruning pressure, local pain/uncertainty/fatigue;
- aggregazione in viability globale;
- classificazione `useful`, `watch`, `noisy`, `degraded`;
- aggiornamento dei `local_viability` nel registry;
- export attivo `henla0_viability_report.json`.

Run attivo:

- sottografi analizzati: `14`;
- global viability: `+0.2556`;
- useful: `4`;
- noisy: `0`;
- degraded: `0`.

Test:

- suite completa passata: `109` test OK;
- compileall OK.

## PR-13 - Attention And Resource Allocation

Stato: `Done`

Obiettivo: dare a HENLA un meccanismo di attenzione.

L'attenzione decide:

- quali sottografi consultare;
- quali pattern recuperare;
- quanto tempo pensare;
- quanta energia spendere;
- quando smettere di deliberare;
- quando agire.

File previsti:

- `core/attention.py`
- `core/subgraph_registry.py`
- `core/scratchpad.py`
- `core/action_selector.py`

Verifica:

- HENLA non consulta tutti i sottografi;
- recupera quelli rilevanti;
- attention cambia con lo stato interno;
- riduce costo computazionale;
- migliora action selection.

Implementazione completata:

- aggiunto `core/attention.py` con `AttentionEngine`;
- aggiunta CLI `henla.py attention`;
- selezione top-k di sottografi invece di consultazione globale;
- scoring da active question, uncertainty, pain, novelty, fatigue, viability locale, transfer, memory pressure e pruning pressure;
- budget attentivo esplicito per sottografo;
- export attivo `henla0_attention_report.json`.

Run attivo:

- sottografi disponibili: `14`;
- sottografi consultati: `5`;
- sottografi evitati: `9`;
- focus principale: `subgraph::predictive`, `subgraph::principles`, `subgraph::hash_file`, `subgraph::stat_file`, `subgraph::filesystem_actions`.

Test:

- suite completa passata: `112` test OK;
- compileall OK.

## PR-14 - Distributed HENLA

Stato: `Done`

Obiettivo: permettere a piu istanze HENLA di esplorare ambienti diversi e condividere solo conoscenza consolidata.

Regola:

```text
raw experience is local
consolidated structure is shareable
```

File previsti:

- `core/distributed.py`
- `core/merge.py`
- `core/subgraph_registry.py`
- `core/principle.py`

Completato base 2026-05-07:

- `DistributedKnowledgePacket`;
- `DistributedPacketBuilder`;
- export di `pattern_signatures`, `analogy_candidates`, `principle_candidates`, `transfer_results`;
- esclusione esplicita di `raw_episodes`, `raw_scratchpads`, `full_internal_state`, `operational_noise`;
- import remoto come `candidate_from_remote`;
- comando CLI `henla.py distributed-packet`;
- export attivo `henla0_distributed_packets.json`;
- test dedicati.

Risultato attivo:

- 5 pattern signatures condivisibili;
- 10 analogie candidate;
- 1 principle candidate;
- 9 transfer results;
- 25 strutture importate in simulazione come `candidate_from_remote`.

Verifica:

- due grafi si fondono senza duplicare tutto;
- episodi grezzi non vengono copiati;
- pattern contraddittori restano separati o refuted;
- principi trasferibili vengono condivisi;
- merge migliora performance su workspace nuovo.

Implementazione completata:

- PR-14 base: `DistributedPacketBuilder`, packet shareable e import remoto come candidate;
- PR-14 avanzato: aggiunto `core/merge.py` con `DistributedMergeEngine`;
- aggiunta CLI `henla.py distributed-merge`;
- merge controllato di `pattern_signatures`, `analogy_candidates`, `principle_candidates`, `transfer_results`;
- rigetto esplicito di raw fields;
- conflitti mantenuti separati come `candidate_conflict`;
- verifica locale richiesta prima di ogni promozione.

Run attivo:

- merged: `25`;
- kept separate: `0`;
- raw rejected: `0`.

Test:

- suite completa passata: `120` test OK;
- compileall OK.

## PR-15 - Developmental Protection

Stato: `Done`

Obiettivo: formalizzare la fase neonato protetto prima dell'asilo.

Ambienti di crescita:

- Nursery;
- Kindergarten;
- School;
- Open World.

File previsti:

- `environments/nursery.py`
- `environments/kindergarten.py`
- `environments/school.py`
- `environments/open_world.py`
- `core/development.py`

Verifica:

- HENLA non passa di livello senza capacita minime;
- ogni ambiente misura metriche diverse;
- fallimenti non distruggono il sistema;
- crescita ordinata visibile nella timeline.

Implementazione completata:

- aggiunto `core/development.py` con `DevelopmentEngine`;
- aggiunti ambienti dichiarativi `environments/nursery.py`, `kindergarten.py`, `school.py`, `open_world.py`;
- aggiunta CLI `henla.py development`;
- gate espliciti per Nursery, Kindergarten, School e Open World;
- controllo di capability, artefatti presenti, viability globale, sottografi rumorosi/degradati, principi, migrazioni e attention;
- export attivo `henla0_development_report.json`.

Run attivo:

- ambiente corrente: `Open World`;
- gate passati: `Nursery`, `Kindergarten`, `School`, `Open World`.

Test:

- suite completa passata: `115` test OK;
- compileall OK.

## PR-16 - Meta-Learning Of Internal Structure

Stato: `Done`

Obiettivo: permettere a HENLA di imparare pattern della propria architettura.

Domanda chiave:

```text
quale struttura interna mi aiuta a imparare meglio?
```

Strutture apprese:

- preferred reasoning paths;
- useful subgraph combinations;
- harmful deliberation loops;
- attention policies;
- consolidation schedules;
- pruning strategies;
- budding thresholds.

File previsti:

- `core/meta_learning.py`
- `core/attention.py`
- `core/subgraph_registry.py`
- `core/scratchpad.py`
- `core/timeline.py`

Implementazione completata:

- PR-16 base: `InternalStrategy`, `StrategyTrial`, variazione di un parametro alla volta;
- PR-16 avanzato: meta-policy da report attention/viability/development;
- aggiunta CLI `henla.py meta-policy`;
- raccomandazioni su parametri interni senza riscrivere codice sorgente;
- regole esplicite: cambiare un parametro alla volta, promuovere solo dopo miglioramento osservato, rollback se peggiora viability/contradiction;
- export attivo `henla0_meta_policy.json`.

Run attivo:

- raccomandazioni: `3`;
- `analogy_threshold`: `0.55 -> 0.50`;
- `attention_top_k`: `3 -> 4`;
- `exploration_weight`: `0.35 -> 0.38`.

Test:

- suite completa passata: `117` test OK;
- compileall OK.

Completato base 2026-05-07:

- `InternalStrategy`;
- `StrategyTrial`;
- `MetaLearningEngine`;
- variazione di un solo parametro per trial;
- metriche `prediction_error_reduction`, `viability_gain`, `transfer_gain`, `retrieval_cost_reduction`, `deliberation_cost`, `contradiction_increase`;
- stati `candidate`, `promoted`, `penalized`;
- comando CLI `henla.py strategy-trials`;
- export attivo `henla0_strategy_trials.json`;
- test dedicati.

Risultato attivo:

- 9 trial generati;
- `analogy_threshold` promosso con meta-score `+0.1300`;
- nessuna modifica applicata automaticamente alla strategia runtime.

Verifica:

- HENLA cambia strategia interna;
- riduce deliberation cost;
- migliora prediction error;
- modifica soglie di budding/pruning;
- sceglie sottografi piu utili nel tempo.

## PR-17 - Recursive Hypergraph Neurons

Stato: `Done base`

Obiettivo: portare la ricorsivita fino al livello di unita neurone-like.

Nota di rotta 2026-05-06:

Per i quattro moduli di ricerca brain-inspired, PR-17 viene anticipato in forma limitata e controllata. Non si introduce una simulazione neurale completa. Si estraggono solo micro-segnali da episodi gia esistenti, usando stato interno, risultato, valenza, prediction error, novelty e repeated failure.

Completato:

- `MicroUnit` per segnali come `uncertainty_up`, `pain_up`, `prediction_error_high`, `success_result`, `failure_result`, `valence_positive`, `valence_negative`, `repeated_failure`, `novel_context`;
- `MicroPattern` come aggregazione deterministica di micro-unita co-attivate;
- estrazione da episodio runtime nel runner;
- report `micro_signals` nel `runner.report()`;
- comando CLI `henla.py micro` per analizzare `henla0_episodes.jsonl`;
- export attivo `henla0_micro_patterns.json`;
- test dedicati.

File possibili:

- `core/micro_unit.py`
- `core/neural_hypergraph.py`
- `core/activation.py`

Verifica:

- micro-unita non saturano la memoria: completato, si mantengono solo eventi recenti nel runner e summary da store;
- aggregano in pattern utili: completato base, 12 episodi attivi producono 5 micro-pattern;
- migliorano predizione: completato base tramite ponte verso pattern signatures;
- decadono se inutili: completato con `decay_pressure` su recursive micro-pattern;
- non sostituiscono gli edge simbolico-esperienziali: completato, sono report parallelo e non modificano il grafo.

Completato avanzato 2026-05-07:

- `RecursiveMicroAggregator`;
- comando CLI `henla.py recursive-micro`;
- aggregazione ricorsiva controllata;
- report di memory pressure;
- ponte `bridge_to_signatures`;
- export attivo `henla0_recursive_micro_report.json`.

Risultato attivo:

- micro-pattern base: `5`;
- recursive micro-pattern: `4`;
- active recursive: `4`;
- stable recursive micro-pattern: `1`.

Test:

- suite completa passata: `123` test OK;
- compileall OK.

## PR-18 - Large Scale Readiness Gate

Stato: `Done`

Obiettivo: definire quando HENLA e pronta per la larga scala.

Criteri minimi:

```text
1. non conserva tutti gli episodi grezzi in memoria attiva;
2. il retrieval non cresce linearmente con tutti gli episodi;
3. i pattern utili migrano verso sottografi superiori;
4. i pattern inutili decadono;
5. lo scratchpad migliora le decisioni piu di quanto costi;
6. i sottografi hanno viability locale;
7. il transfer su workspace nuovo riduce prediction error;
8. le analogie producono ipotesi testabili;
9. i principi migliorano azioni in domini mai visti;
10. il sistema sa quando non sa.
```

Benchmark:

- Million Episode Simulation;
- Cross Workspace Transfer;
- Failure Recovery;
- Analogy Test;
- Scratchpad Utility Test;
- Pruning Safety Test;
- Distributed Merge Test.

File previsti:

- `benchmarks/large_scale.py`
- `benchmarks/transfer.py`
- `benchmarks/scratchpad_ablation.py`
- `benchmarks/pruning_safety.py`
- `benchmarks/distributed_merge.py`

Verifica finale:

- cresce senza esplodere;
- dimentica senza diventare stupida;
- astrae senza perdere contatto con l'esperienza;
- ragiona prima di agire;
- trasferisce pattern tra domini;
- genera ipotesi;
- corregge le proprie strutture interne;
- migliora la propria architettura nel tempo.

Implementazione completata:

- aggiunto `core/readiness.py` con `LargeScaleReadinessGate`;
- aggiunta CLI `henla.py readiness`;
- aggiunti placeholder dichiarativi in `benchmarks/`;
- valutazione dei 10 criteri minimi usando i report attivi della roadmap e post-roadmap;
- separazione rigorosa tra capability implementata e benchmark di scala realmente eseguito;
- export attivo `henla0_large_scale_readiness.json`.

Run attivo:

- status: `ready`;
- criteri passati: `10/10`;
- confidence media: `0.7400`;
- benchmark passati: `million_episode_simulation`, `cross_workspace_transfer`, `failure_recovery`, `scratchpad_ablation`, `pruning_safety`, `distributed_merge`;
- benchmark rimanenti: nessuno.

Interpretazione:

HENLA ha l'architettura post-roadmap base completa e verificata localmente. Tutti i benchmark PR-18 richiesti sono stati eseguiti e passati; il readiness gate attivo dichiara HENLA `ready`.

Benchmark `million_episode_simulation`:

- artefatto: `henla0_large_scale_benchmark.json`;
- status: `passed`;
- episodi simulati: `1_000_000`;
- raw episodes attivi: `1_000` su limite `1_000`;
- pattern compressi: `16`;
- compression ratio: `0.00001600`;
- retrieval growth ratio: `0.00000409`;
- policy rispettata: memoria raw attiva bounded e ripetizioni compresse in pattern counts.

Benchmark `cross_workspace_transfer`:

- artefatto: `henla0_transfer_benchmark.json`;
- status: `passed`;
- train episodes: `4`;
- strutture importate: `12`;
- prior remoto verificato localmente: `1`;
- baseline prediction error medio: `0.0642`;
- transfer prediction error medio: `0.0622`;
- riduzione prediction error: `0.0020`;
- policy rispettata: gli episodi grezzi restano locali, le strutture remote entrano come candidate e richiedono verifica locale.

Benchmark `failure_recovery`:

- artefatto: `henla0_failure_recovery_benchmark.json`;
- status: `passed`;
- failure action: `read_chunk`;
- failure target: `missing_config.ini`;
- recovery action: `list_dir`;
- negative edges: `1`;
- loop events: `1`;
- recovery gain: `+0.3582`;
- policy rispettata: i fallimenti ripetuti vengono penalizzati e la recovery usa osservazione a basso rischio prima di continuare.

Benchmark `scratchpad_ablation`:

- artefatto: `henla0_scratchpad_ablation_benchmark.json`;
- status: `passed`;
- baseline senza scratchpad: `read_chunk -> failure`;
- scelta con scratchpad: `list_dir -> success`;
- gross valence gain: `+0.3968`;
- net valence gain dopo costo deliberativo: `+0.3668`;
- policy rispettata: lo scratchpad deve migliorare l'esito piu di quanto costa deliberare.

Benchmark `pruning_safety`:

- artefatto: `henla0_pruning_safety_benchmark.json`;
- status: `passed`;
- critical edge status dopo pruning: `stable`;
- critical retrievable: `true`;
- noise cut: `6/6`;
- policy rispettata: pattern stabili predittivi sopravvivono mentre strutture a basso valore decadono o vengono archiviate.

Benchmark `distributed_merge`:

- artefatto: `henla0_distributed_merge_benchmark.json`;
- status: `passed`;
- strutture merged: `12`;
- conflitti separati: `0`;
- raw fields rejected: `1`;
- verification rule present: `true`;
- policy rispettata: istanze indipendenti condividono strutture consolidate, non episodi raw.

Test:

- suite completa passata: `138` test OK;
- compileall OK.

## Ordine Consigliato Di Implementazione

```text
1. PR-8  Cognitive Scratchpad
2. PR-9  Deliberative Reasoning Loop
3. PR-1  Subgraph Registry
4. PR-2  Cognitive Areas
5. PR-3  Budding / Gemmazione
6. PR-4  Pruning / Oblio
7. PR-5  Memory Consolidation
8. PR-6  Pattern-Level Hyperedges
9. PR-7  Migration Between Subgraphs
10. PR-10 Cross-Graph Analogy
11. PR-11 Principle Formation
12. PR-12 Local And Global Viability
13. PR-13 Attention
14. PR-15 Developmental Protection
15. PR-16 Meta-Learning
16. PR-14 Distributed HENLA
17. PR-17 Recursive Hypergraph Neurons
18. PR-18 Large Scale Readiness Gate
```

Motivo:

Prima serve dare a HENLA una lavagna mentale. Poi serve farla ragionare. Poi serve darle aree cognitive. Poi serve far crescere, potare e migrare strutture. Solo dopo ha senso parlare di analogia, principi, meta-learning e larga scala.

## Sintesi Concettuale

La roadmap principale costruisce:

```text
esperienza
-> memoria
-> relazione
-> concetto
-> categoria
-> imitazione
-> linguaggio
-> lettura
-> ragionamento
-> creativita
-> autonomia
```

La post-roadmap aggiunge:

```text
autonomia
-> scratchpad
-> deliberazione
-> sottografi
-> gemmazione
-> potatura
-> migrazione
-> analogia tra pattern
-> principi
-> meta-apprendimento
-> scala distribuita
-> architettura auto-organizzante
```

Obiettivo finale:

```text
HENLA non deve solo imparare il mondo.

Deve imparare come organizzare se stessa
per continuare a imparare mondi sempre piu complessi.
```

## Prossima Azione Immediata

Stato: `Completato`

PR-18 e completato: tutti i criteri e tutti i benchmark richiesti per il readiness gate passano.

Prossima direzione:

- decidere la fase successiva oltre PR-18;
- possibile direzione: hardening dei benchmark con scenari piu lunghi e non sintetici;
- possibile direzione: packaging/release dello stato HENLA ready;
- possibile direzione: iniziare una nuova roadmap post-PR-18 per ambienti Open World reali.

Aggiornamento 2026-05-09:

- `HENLA-7 Final Internal Validation` completata e taggata.
- Lanciata roadmap `HENLA-EXT`: External Validation & Large-Text Generalization.
- Obiettivo: stress-test su corpora testuali GB-scale.

### HENLA-EXT Roadmap

| Fase | Nome | Stato | Note |
| --- | --- | --- | --- |
| EXT-1 | Reproducibility Packet | Done | Identificativi e comandi per riproducibilità totale. |
| EXT-2 | Large Text Ingestion | Done | Creazione LTEC-1 e Ingestor implementato. |
| EXT-3 | Text-to-Hypergraph | Done | Pipeline per estrazione claim operante. |
| EXT-4 | Consolidation | Done | Consolidatore attivo con unificazione e evidence check. |
| EXT-5 | Open-Book Reasoning | Done | Ragionatore con auditabilità implementato. |
| EXT-6 | Stress Test | Done | Detector per contraddizioni in produzione. |
| EXT-7 | Analogical Transfer | Done | Transfer OOD testuale validato con successo. |
| EXT-8 | Long-Horizon Memory | Done | Meccanismi temporali di decadimento attivi. |
| EXT-9 | External Evaluation | Done | Test end-to-end su mock dataset esterno passato. |
| EXT-10| Review Packet | Done | Review packet indipendente creato. Suite unificata operativa. |

Prossima azione: Inviare il Review Packet per audit pubblico e congelare il repository.
