# ISEE Framework integration

> Put governed Intent, Structure, Execution, and Evidence into an ordinary
> GitHub Copilot session or an automated agentic flow.

ISEE is the operating framework for AI-native engineering teams. Read the
framework overview at [agentile.org](https://agentile.org).

This repository is the thin user-facing integration over:

- [ADRP](https://github.com/suuus/adrp) — durable Intent;
- [ASRP](https://github.com/suuus/asrp) — durable Structure;
- execution agents and platforms;
- [AERP](https://github.com/suuus/aerp) — durable Evidence.

It does not duplicate their standards. It orchestrates their deterministic
CLIs and projects the result into files GitHub Copilot already understands.

## Install

Install the complete [ISEE plugin suite](https://github.com/suuus/isee-plugins):

```bash
copilot plugin marketplace add suuus/isee-plugins
copilot plugin install isee-suite@isee
```

Then select `/agent isee`. The suite also includes the ADRP, ASRP, AERP, and
ISEE Advisor agents and skills. Use `isee-setup` to install or diagnose the
deterministic CLIs.

To load only this integration plugin:

```bash
copilot plugin install isee@isee
```

## Regular Copilot session

```bash
isee init

isee preflight \
  --decisions .github/decisions \
  --structures .github/structures \
  --scope "this repository" \
  --entry-point repository-development \
  --action "Implement the requested change"
```

This creates:

```text
.github/
├── instructions/
│   └── isee.instructions.md
└── isee/
    ├── active-intent.json
    ├── execution-manifest.json
    ├── context.md
    └── preflight.json
```

Copilot CLI automatically loads `.github/instructions/**/*.instructions.md`.
For a one-off session:

```text
@.github/isee/context.md
@.github/isee/execution-manifest.json

Implement the requested change.
```

## Agentic flow

```text
isee preflight
    ↓
human or policy approval
    ↓
execution agent or platform
    ↓
AERP Evidence capture and verification
    ↓
isee evaluate
```

Evaluate the outcome:

```bash
isee evaluate \
  --manifest .github/isee/execution-manifest.json \
  --evidence evidence/bundle.json
```

The evaluation verifies that Evidence carries the expected ADRP and ASRP
bindings and satisfies the manifest's Evidence requirements.

## Commands

```bash
isee init
isee doctor
isee project --intent-resolution resolved.json --manifest manifest.json
isee preflight --decisions ... --structures ... --scope ... --entry-point ... --action ...
isee evaluate --manifest ... --evidence ...
```

## Documentation

- [Regular Copilot usage](docs/REGULAR_COPILOT.md)
- [Agentic flows](docs/AGENTIC_FLOW.md)
- [Architecture and trust boundaries](docs/ARCHITECTURE.md)

## Status

ISEE integration `0.1.0` is alpha. It orchestrates deterministic local tools;
approval, signing, producer authentication, policy applicability, and execution
remain explicit external boundaries.

## License

[MIT](LICENSE)
