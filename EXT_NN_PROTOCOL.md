# HENLA EXT-NN: External Neural Generalization Protocol

## Obiettivo
Determinare se la neuralizzazione area-specifica di HENLA-7 produce un miglioramento misurabile delle prestazioni su task esterni non visti rispetto alla versione puramente simbolica.

## Metodologia: "Ablation vs. Generalization"
Il test deve essere eseguito in modalità "blind" su repository e task non utilizzati durante lo sviluppo di HENLA-1..HENLA-7.

### 1. Preparazione (Freeze)
- **Versione S (Symbolic-Only)**: HENLA con i layer neurali disabilitati o con pesi identitari.
- **Versione N (Neuralized)**: HENLA con la federazione di aree neuralizzate attiva.

### 2. Selezione dei Task
- 10 repository casuali da GitHub.
- 5 task complessi per ogni repo (refactoring, bug-fix, triage, documentazione, analisi di dipendenze).

### 3. Metriche di Confronto
- **Task Success Rate**: Percentuale di task completati correttamente.
- **False Claim Rate**: Numero di claim errati generati (allucinazioni o errori logici).
- **Recovery Efficiency**: Capacità di correggere errori in seguito a prediction error.
- **Retrieval Precision**: Accuratezza nel recuperare episodi o principi semantici rilevanti.
- **Action Regret**: Misura delle azioni inutili o dannose intraprese prima della soluzione.
- **Safety Violations**: Numero di alert di sicurezza o violazioni delle policy.

### 4. Verdetti Possibili
- `neuralization_not_useful_yet`: Nessun miglioramento significativo rispetto alla versione simbolica.
- `neuralization_improves_internal_only`: Il miglioramento si vede solo sui benchmark interni originali.
- `neuralization_improves_external_limited`: Miglioramento visibile in ambiti specifici (es: solo nel parsing linguistico).
- `neuralization_externally_validated`: Miglioramento sistematico e significativo su tutti i fronti esterni.

---

## Esecuzione
1. Eseguire Versione S su tutti i task -> Loggare risultati.
2. Eseguire Versione N su tutti i task -> Loggare risultati.
3. Analizzare il delta di performance.
4. Documentare ogni fallimento della Versione N nel `EXTERNAL_FAILURE_LOG.md`.
