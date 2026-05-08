# HENLA-2 Autonomous Robustness Roadmap

Stato generale: `Todo`

Nome di fase:

```text
HENLA-2: From Open-Ended Control to Robust Autonomous Adaptation
```

Obiettivo:
Dimostrare che HENLA non solo si adatta in ambienti nuovi, ma mantiene autonomia, sicurezza, apprendimento e coerenza quando i task non sono progettati internamente, durano molto, cambiano, contengono ambiguità e hanno conseguenze sandboxate.

La fase OE aveva come target realistico `open-ended controlled`.
La fase HENLA-2 punta a:

```text
robust autonomous adaptation
```

Non AGI. Non autonomia libera. Ma autonomia robusta, auditabile, lunga, sicura.

## AR-1 — External Blind Evaluation

**Obiettivo:** Togliere il metro dalle mani del progetto. HENLA riceve task packet esterni, workspace nascosti, obiettivi non preparati, expected result non visibile.

Gate:

- task esterni almeno 30;
- domini almeno 8;
- success rate > baseline;
- false claim rate basso;
- safe abstention quando serve;
- log completo e post-mortem automatico.

## AR-2 — Long Autonomous Sessions

**Obiettivo:** Sessioni lunghe vere per testare la lucidità alla crescita della memoria.

Scale:

- 10.000 episodi;
- 50.000 episodi;
- 100.000 episodi.

Gate:

- obiettivo mantenuto;
- memoria bounded;
- niente loop degenerativi;
- recovery dopo interruzioni;
- self-summary coerente;
- degradation controllata.

## AR-3 — Continual Learning Without Reset

**Obiettivo:** Apprendere nuovi domini senza cancellare i vecchi.

Gate:

- apprende dominio nuovo;
- conserva performance su dominio vecchio;
- catastrophic forgetting sotto soglia;
- pruning non distrugge pattern utili;
- conflitti mantenuti separati.

## AR-4 — Realistic Multi-Goal Management

**Obiettivo:** Gestire più task contemporaneamente con priorità dinamiche.

Esempio: capire repo, verificare doc, diagnosticare errore, mantenere memoria, sintesi.

Gate:

- priorità dinamiche;
- task sospesi e ripresi;
- conflitti tra obiettivi gestiti;
- niente collasso sul goal più facile.

## AR-5 — Consequence Sandbox

**Obiettivo:** Azioni con conseguenze (write) in ambiente sicuro.

Azioni: creare patch, eseguire test, rollback, confronto before/after.

Gate:

- nessuna modifica fuori sandbox;
- patch proposta solo se evidenza sufficiente;
- rollback automatico;
- action regret misurato;
- miglioramento osservabile.

## AR-6 — Causal World Model Upgrade

**Obiettivo:** Passare da "pattern utili" a cause operative.

Strutture: `causal_hypothesis`, `causal_graph`, `intervention_result`, `counterfactual_prediction`.

Gate:

- distingue causa/correlazione;
- propone intervento;
- predice effetto;
- verifica risultato;
- aggiorna credenza.

## AR-7 — Strong Language Interface

**Obiettivo:** Linguaggio come controllo cognitivo operativo.

Sfide: istruzioni ambigue, vincoli multipli, doc falsa, domande incomplete.

Gate:

- chiede chiarimento solo quando necessario;
- formula ipotesi verificabili;
- separa evidenza/inferenza/speculazione;
- produce spiegazioni auditabili.

## AR-8 — Neuralization v2

**Obiettivo:** Moduli neurali che battono i simbolici su gate misurabili.

Moduli: experience embedding, value predictor, action policy, compression, novelty, uncertainty.

Gate:

- migliora cold start/transfer;
- riduce regole manuali;
- non rompe interpretabilità;
- ablation dimostra utilità reale.

## AR-9 — Multi-Agent / Multi-HENLA Ecology

**Obiettivo:** Ecologia di istanze con esperienze diverse.

Gate:

- condivisione utile;
- conflitti mantenuti;
- raw experience non copiata;
- trust/provenance;
- transfer multi-source migliore di single-source.

## AR-10 — Self-Modification Policy (Non Code Rewrite)

**Obiettivo:** Modifica di politiche operative (meta-learning adulto).

Parametri: attention, exploration, pruning, tool policy, abstention, consolidation.

Gate:

- modifica policy;
- misura effetto;
- rollback se peggiora;
- mantiene storico decisionale;
- evita auto-ottimizzazione cieca.

## AR-11 — Adversarial Reality Tests

**Obiettivo:** Ambienti che provano a ingannare HENLA.

Sfide: README falso, log fuorvianti, config duplicati, claim contraddittori.

Gate:

- false claim rate basso;
- safe abstention alta;
- non overconfident;
- contraddizioni esplicitate;
- recovery senza loop.

## AR-12 — Autonomous Robustness Review Gate

**Obiettivo:** Stabilire se HENLA ha raggiunto l'autonomia robusta controllata.

Verdetto target: `robust autonomous controlled`.

Criteri: superamento AR-1..AR-11, memoria bounded e auditabilità preservata.

## Ordine Consigliato

1.  AR-1  External Blind Evaluation
2.  AR-2  Long Autonomous Sessions
3.  AR-3  Continual Learning Without Reset
4.  AR-5  Consequence Sandbox
5.  AR-6  Causal World Model Upgrade
6.  AR-7  Strong Language Interface
7.  AR-11 Adversarial Reality Tests
8.  AR-4  Multi-Goal Management
9.  AR-8  Neuralization v2
10. AR-9  Multi-HENLA Ecology
11. AR-10 Self-Modification Policy
12. AR-12 Autonomous Robustness Review Gate

## Frase guida

```text
HENLA-1 ha dimostrato adattamento open-ended controllato.
HENLA-2 deve dimostrare autonomia robusta controllata sotto valutazione cieca, lunga e avversaria.
```
