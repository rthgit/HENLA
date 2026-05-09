# HENLA-EXT-1: Reproducibility Packet

Questo documento fornisce le istruzioni necessarie per riprodurre i risultati della fase HENLA-7 (Internal Validation) e avviare la fase EXT.

## 1. Identificativi della Release
- **Repository**: `https://github.com/rthgit/HENLA`
- **Tag**: `henla-7-final-internal-validation`
- **Commit Hash**: `c232985` (o l'hash più recente del tag final)
- **Versione Core**: `v0.7.0-final-internal`

## 2. Ambiente di Esecuzione
- **Hardware**: CPU standard (per core simbolico) + GPU (NVIDIA T4, A40 o equivalente per training/inferenza neurale).
- **Python**: 3.10 / 3.11
- **Dipendenze**: `pip install -r requirements.txt`

## 3. Comandi di Riproduzione

### A. Validazione Interna (Neural Civilization Suite)
```bash
python -m benchmarks.run_neural_civilization_suite
```
**Expected Output**: JSON con `verdict: NEURAL_CIVILIZATION_READY` e `5/5` criteri passati.

### B. Validazione Ponte Analogico (GPU-8)
```bash
python -m benchmarks.gpu_8_analogical_bridge
```
**Expected Output**: `.benchmark_runs/gpu8/henla0_gpu8_results.json` con `status: passed`.

### C. Gate Quantitativo OOD (GPU-9)
```bash
python -m benchmarks.gpu_9_ood_analogical_generalization
```
**Expected Output**: `.benchmark_runs/gpu9/henla0_gpu9_results.json` con un `delta_improvement` positivo (atteso ~25%) rispetto alla baseline procedurale.

## 4. Dataset & Pesi
- **Dataset**: UEC v4.1 (incluso negli artefatti della release).
- **Modelli**: Pesi in `artifacts/neural/models/` (TargetPredictor, APHM v2).

## 5. Baseline di Confronto
Tutti i test OOD confrontano:
1. `procedural_only`: Policy neurale locale senza recupero analogico.
2. `analogical_bridge`: Flusso integrato con arbitrato su ipergrafo astratto (APHM v2).

## 6. Claim Boundary
Consultare [CLAIM_BOUNDARY.md](CLAIM_BOUNDARY.md) per i limiti legali e scientifici del progetto.

## 7. Contatti & Audit
Per audit indipendenti o segnalazioni di mancata riproducibilità, aprire una Issue su GitHub con etichetta `EXT-REPRO-FAIL`.
 stone
 stone
 stone
