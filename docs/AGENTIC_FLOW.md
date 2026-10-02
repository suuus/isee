# Agentic flow

Install the complete Copilot workflow from
[suuus/isee-plugins](https://github.com/suuus/isee-plugins). The conceptual
framework is documented at [agentile.org](https://agentile.org).

## Preflight

`isee preflight` performs deterministic tool orchestration:

1. ADRP set verification;
2. ADRP scope resolution;
3. ADRP autonomy evaluation;
4. ASRP Structure resolution and manifest compilation;
5. Copilot projection generation.

The generated manifest is the stable handoff into Execution.

## Execution

An execution platform receives:

- exact Intent bindings;
- exact Structure bindings;
- entry point and runner;
- required elements and gates;
- Evidence obligations;
- manifest fingerprint.

Changing any of these requires a new manifest.

## Closure

After AERP capture:

```bash
isee evaluate \
  --manifest .github/isee/execution-manifest.json \
  --evidence evidence/bundle.json
```

Evaluation checks binding completeness and Evidence obligations. Signature,
identity, compliance, and human acceptance remain separate gates.
