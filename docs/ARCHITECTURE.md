# Architecture

```text
ISEE agent and CLI
  ├── orchestrates adrp
  ├── orchestrates asrp
  ├── projects Copilot instructions
  └── evaluates aerp
```

ISEE does not reimplement the three profiles. The CLIs remain independently
usable and independently enforce their schemas and fingerprints.

## Trust boundaries

| Boundary | Owner |
|---|---|
| Decision authority and standing | ADRP |
| Architecture, ownership, gates, entry points | ASRP |
| Work execution | Selected external system |
| Evidence semantics and artifact integrity | AERP |
| Orchestration and Copilot projection | ISEE |
| Signatures and producer authentication | External attestation system |
| Compliance standing | Applicable governance process |

The ISEE projection is disposable and regenerable. Canonical ADRP, ASRP, and
AERP records remain the durable sources.
