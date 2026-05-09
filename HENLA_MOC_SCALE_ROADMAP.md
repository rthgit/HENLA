# HENLA-MoC-SCALE Roadmap
**Federazione di LLM area-specifiche + scratchbook + ipergrafo condiviso**

## Principio Architetturale
HENLA-SCALE is a federated cognitive LLM architecture: multiple area-specific language models are trained on the same experience stream, but each area optimizes different cognitive targets. Their outputs are written into a shared deliberative scratchbook and consolidated through hypergraph memory and neuro-symbolic arbitration into one final answer or action.

Non agente sopra transformer. Non un LLM unico. Non tool wrapper.

---

## SCALE-1 — FineWeb/FineWeb-Edu Massive Corpus
- **Obiettivo**: Usare FineWeb-Edu come punto di partenza per i primi training seri.
- **Scala proposta**:
  - Corpus-0: 100MB sanity
  - Corpus-1: 1GB
  - Corpus-2: 10GB
  - Corpus-3: 100GB
  - Corpus-4: 1TB
  - Corpus-5: multi-TB
- **Struttura**: Ogni documento diventa un'esperienza strutturata (testo + entità + archi + target di area).

## SCALE-2 — Shared Experience Stream
- **Obiettivo**: Stesso testo testuale → aree diverse → apprendimento diverso.
- **Dinamica**: Ogni chunk entra una volta nello stream comune. Ogni area estrae e apprende aspetti completamente diversi (es. Semantic estrae relazioni, Procedural estrae azioni, Analogical estrae pattern).

## SCALE-3 — Area-Specific LLM Contracts
- **Obiettivo**: Definire input schema, output schema, losses, permessi di read/write dell'ipergrafo e metriche per le 8 aree:
  1. Episodic LLM
  2. Semantic LLM
  3. Procedural LLM
  4. Predictive LLM
  5. Analogical LLM
  6. Linguistic LLM
  7. Safety LLM
  8. Metacognitive LLM

## SCALE-4 — Scratchbook as Fusion Layer
- **Obiettivo**: Lo scratchbook è il registro strutturato dove le aree diventano una mente unica.
- **Dinamica**: Output delle aree → Scratchbook → Arbitrator → One answer / One action.

## SCALE-5 — Model Size Ladder
- **Obiettivo**: Scalare per federazione, non per singolo modello gigante.
- **Ladder**:
  - Micro: 8 x 10M = 80M
  - Tiny: 8 x 25M = 200M
  - Small: 8 x 125M = 1B
  - Base: 8 x 350M = 2.8B
  - Large: 8 x 1.3B = 10.4B
  - XL: 8 x 3B = 24B

## SCALE-6 — Parameter Golf
- **Obiettivo**: Trovare la configurazione minima che mostra vantaggio cognitivo rispetto a un transformer monolitico.
- **Domanda**: A parità di parametri totali, HENLA-MoC batte un singolo Transformer? (es. 8 x 125M vs 1B single).

## SCALE-7 — Training Stages
- **Stage A**: Area Pretraining
- **Stage B**: Scratchbook Writing
- **Stage C**: Hypergraph Read/Write
- **Stage D**: Inter-Area Message Training
- **Stage E**: Arbitrator Training
- **Stage F**: Joint Adapter Training
- **Stage G**: Selective Joint Training

## SCALE-8 — Distributed Multi-Model Training
- **Obiettivo**: Infrastruttura per stream dataloaders, FSDP/DeepSpeed, checkpoint separati per area.

## SCALE-9 — Evaluation
- **Obiettivo**: Benchmark centrali (MoC vs Single Model, Ablazioni).
- **Regola**: Il sistema deve dimostrare di battere un modello unico a parità di budget computazionale o parametri.

## SCALE-10 — Billion-Parameter Target
- **Obiettivo**: Scalare a miliardi di parametri.
- **Gate**: Non aumentare parametri se la scala precedente non batte le baseline e le ablazioni.
