# HENLA-EXT: External Validation & Large-Text Generalization Program

## Obiettivo
Sottoporre l'architettura HENLA-7 (congelata e validata internamente) a stress-test su corpora testuali di larga scala (GB di testo reale) per verificare la tenuta di memoria, ipergrafi, arbitrato e transfer analogico in condizioni non controllate.

---

## Roadmap HENLA-EXT

### HENLA-EXT-1 — Reproducibility Packet
**Obiettivo:** Rendere HENLA-7 riproducibile da terzi. Include tag, hash, comandi, output attesi e claim boundary.
**Output:** `HENLA_EXT_REPRODUCIBILITY_PACKET.md`.

### HENLA-EXT-2 — Large Text Ingestion
**Obiettivo:** Trasformare grandi quantità di testo reale (manuali, issue, paper) in esperienza strutturata.
**Output:** `LTEC-1 (Large Text Experience Corpus v1)`.

### HENLA-EXT-3 — Text-to-Hypergraph Pipeline
**Obiettivo:** Estrazione di claim, evidenze, contraddizioni e pattern da testo grezzo verso strutture a ipergrafo auditabili.

### HENLA-EXT-4 — Knowledge Consolidation
**Obiettivo:** Gestire la crescita dei dati evitando l'esplosione del rumore. Fusione nodi, unificazione claim, compressione episodi.

### HENLA-EXT-5 — Open-Book Reasoning
**Obiettivo:** Rispondere a task complessi usando il corpus LTEC-1, fornendo tracce di evidenza e incertezza.

### HENLA-EXT-6 — Contradiction & Uncertainty Stress Test
**Obiettivo:** Verificare la capacità di HENLA di gestire informazioni conflittuali senza collassare in risposte false.

### HENLA-EXT-7 — Analogical Transfer on Text
**Obiettivo:** Applicare i pattern appresi da un dominio testuale per risolvere problemi in domini OOD reali.

### HENLA-EXT-8 — Long-Horizon Memory
**Obiettivo:** Testare la memoria nel tempo: aggiornamento credenze, rimozione conoscenza obsoleta, provenance.

### HENLA-EXT-9 — External Corpus Evaluation
**Obiettivo:** Validazione su dataset pubblici esterni (arXiv, GitHub dumps, RFC) per evitare bias di selezione.

### HENLA-EXT-10 — Independent Review Packet
**Obiettivo:** Preparazione del pacchetto finale per revisori esterni, inclusi i casi di fallimento e le limitazioni note.

---

## Criterio di Successo Finale
HENLA-EXT è considerata conclusa quando il sistema dimostra miglioramenti misurabili nel ragionamento evidence-grounded e nel transfer analogico su scala GB rispetto a baseline di retrieval standard.
