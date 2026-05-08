# HENLA-3 Recursive Self-Improvement & Meta-Reasoning Roadmap

## Principio guida

```text
HENLA non modifica direttamente se stessa.
HENLA propone, testa, misura, confronta e solo poi promuove.
```

Ogni miglioramento deve seguire questo ciclo:

```text
limite osservato
→ ipotesi di miglioramento
→ patch/proposta in sandbox
→ benchmark comparativo
→ ablation
→ safety check
→ rollback possibile
→ promozione solo se gate superato
```

Verdetti finali possibili:

```text
blocked
experimental self-improvement
controlled recursive improvement
robust recursive meta-reasoning
```

Target realistico:

```text
controlled recursive improvement
```

---

## RSI-1 — Architecture Self-Diagnosis
**Obiettivo:** HENLA deve analizzare i propri fallimenti e limiti architetturali.
- **Output:** failure clusters, root cause hypotheses, affected modules, evidence traces, confidence levels.
- **Gate:** Identifica almeno 5 limiti reali, collega a evidenza, distingue bug da limiti architetturali.

## RSI-2 — Hypothesis Generator for Self-Improvement
**Obiettivo:** Generare ipotesi di miglioramento strutturate.
- **Esempio:** Alzare abstention threshold per ridurre false claims.
- **Gate:** Ipotesi testabili, metriche previste, rischi dichiarati.

## RSI-3 — Safe Patch Sandbox
**Obiettivo:** Creare modifiche solo in copie isolate.
- **Limiti:** Solo parametri, policy, threshold, plugin. Nessun accesso al runner principale.
- **Gate:** Reversibilità, diff leggibile, rollback automatico.

## RSI-4 — Comparative Experiment Engine
**Obiettivo:** Ogni proposta deve battere una baseline.
- **Confronti:** Baseline vs Candidate vs Ablation vs Stress Test.
- **Gate:** Miglioramento stabile, nessuna regressione safety, no overfitting.

## RSI-5 — Self-Improvement Memory
**Obiettivo:** Ricordare cosa è stato provato e perché.
- **Struttura:** ImprovementTrial (problem, hypothesis, patch, metrics, accepted/rejected, reason).
- **Gate:** Evita ripetizioni, recupera esperimenti simili.

## RSI-6 — Meta-Reasoning Trace
**Obiettivo:** Rendere auditabile il ragionamento di miglioramento.
- **Trace:** Problem, evidence, options, reasoning, risk assessment.
- **Gate:** Spiegabilità architetturale, distinzione tra evidenza e speculazione.

## RSI-7 — Regression Guardian
**Obiettivo:** Impedire che un miglioramento rompa vecchie funzionalità.
- **Gate:** Safety costante, memory bounded, false claim rate sotto soglia, vecchi benchmark passati.

## RSI-8 — Benchmark Integrity Monitor
**Obiettivo:** Evitare reward hacking.
- **Controlli:** Hash dei test, separazione train/eval, hidden packets.
- **Gate:** Nessuna modifica ai gate, benchmark hash invariato.

## RSI-9 — Recursive Improvement Loop v1
**Obiettivo:** Chiudere un ciclo completo di miglioramento.
- **Gate:** Almeno 3 cicli completi, 1 accettato, 1 rifiutato correttamente, no regressioni.

## RSI-10 — Meta-Learning of Improvement Strategies
**Obiettivo:** Imparare quali strategie di miglioramento funzionano meglio.
- **Gate:** Classifica strategie per successo storico, evita strategie ad alto rischio in incertezza.

## RSI-11 — Self-Generated Test Design
**Obiettivo:** HENLA propone test per scoprire i propri limiti.
- **Gate:** Genera test che espongono debolezze reali, non abbassa i criteri di certificazione.

## RSI-12 — External Audit Interface
**Obiettivo:** Preparare report per revisione umana/esterna.
- **Gate:** Report completi su modifiche, rischi, regressioni e claim boundaries.

## RSI-13 — Controlled Plugin Evolution
**Obiettivo:** Permettere nuove capacità tramite plugin isolati.
- **Gate:** Interfaccia stabile, ablation positiva, rimozione sicura.

## RSI-14 — Multi-HENLA Self-Improvement Ecology
**Obiettivo:** Istanze con ruoli diversi (explorer, critic, guardian) collaborano al miglioramento.
- **Gate:** Conflitti esplicitati, consenso basato su evidenza.

## RSI-15 — Recursive Self-Improvement Review Gate
**Obiettivo:** Validazione finale dell'intera roadmap.
- **Verdetto:** CONTROLLED RECURSIVE IMPROVEMENT.
