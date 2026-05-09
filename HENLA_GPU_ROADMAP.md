# HENLA-GPU: Cloud Neural Training & External Validation Roadmap

## Obiettivo
Sfruttare infrastruttura GPU (NVIDIA A40 48GB) per addestrare, validare e confrontare i sottografi neuralizzati area-specifici di HENLA-7 contro la baseline simbolica pura, producendo evidenza empirica della generalizzazione su task esterni.

## Principio di Rigore
"La GPU non serve a confermare la narrativa, ma a tentare di distruggerla: ogni miglioramento neurale deve essere misurato contro una baseline simbolica congelata."

---

## FASE 1: Setup & Riproducibilità (GPU-0, GPU-1)
- **GPU-0 — Cloud Machine Setup**: Installazione ambiente CUDA/PyTorch su Ubuntu (A40).
- **GPU-1 — Cloud Reproducibility Snapshot**: Generazione di `GPU_ENVIRONMENT_REPORT.json` e freeze dell'ambiente.

## FASE 2: Data Engineering (GPU-2)
- **GPU-2 — Dataset Extraction**: Esportazione di dataset bilanciati (Train/Val/Test) per ogni area:
  - Episodico (Sequence/Novelty)
  - Procedurale (Action/Policy)
  - Predittivo (Valence/Error)
  - Semantico/Analogico (Relations/Mapping)

## FASE 3: Baseline & Training (GPU-3..GPU-9)
- **GPU-3 — Baseline Symbolic Run**: Esecuzione di HENLA in modalità "symbolic-only" per stabilire lo zero-point.
- **GPU-4 — Valence Predictor Training**: Primo training neurale per predire valenza ed errore.
- **GPU-5 — Episodic Encoder Training**: Addestramento contrastivo per retrieval episodico.
- **GPU-6 — Procedural Policy Training**: Ranking neurale delle azioni candidate.
- **GPU-7 — Neural Retrieval Ranker**: Ottimizzazione del recupero della conoscenza.
- **GPU-8 — Semantic/Analogical Training**: Addestramento per pattern mapping tra domini.
- **GPU-9 — Safety & Uncertainty Models**: Modelli per la rilevazione di rischio e overconfidence.

## FASE 4: Governance & Integrazione (GPU-10, GPU-11)
- **GPU-10 — Model Registry**: Tracciamento di ogni peso salvato, hash del dataset e config.
- **GPU-11 — Neuro-Symbolic Integration**: Confronto S vs N vs S+N (Arbitrato).

## FASE 5: Il Test Finale (GPU-12)
- **GPU-12 — EXT-NN External Test**: Blind test su repository/task mai visti con pubblicazione dei fallimenti.

---

## Architettura Cloud
```text
cloud/
  setup_a40_ubuntu.md
  run_gpu_training.sh
  run_gpu_eval.sh
artifacts/
  neural/
    datasets/
    models/
    model_registry.json
```

Verdetto Finale Target: `NEURALIZATION_EXTERNALLY_VALIDATED` o `NEURALIZATION_NOT_USEFUL_YET`.
