# Regular GitHub Copilot usage

## Install the suite

```bash
copilot plugin marketplace add suuus/isee-plugins
copilot plugin install isee-suite@isee
```

Select `/agent isee`. The suite includes all specialist agents and skills; no
`/add-dir` commands or manual copying are required.

## Repository setup

```bash
isee init
```

After ADRP decisions and ASRP Structure exist:

```bash
isee preflight \
  --decisions .github/decisions \
  --structures .github/structures \
  --scope "this repository" \
  --entry-point repository-development \
  --action "Implement issue 42"
```

The generated `.github/instructions/isee.instructions.md` is loaded by Copilot
CLI as repository instructions. The concise `.github/isee/context.md` avoids
forcing every prompt to carry complete rich records.

## One session

Use file mentions:

```text
@.github/isee/context.md
@.github/isee/execution-manifest.json

Implement issue 42. Stop if a blocking gate cannot be satisfied.
```

## Local plugin development only

Copilot CLI can trust and load local agents and skills with:

```text
/add-dir ../adrp
/add-dir ../asrp
/add-dir ../aerp
/add-dir ../isee
/agent isee
```

Published plugins can be managed through `/plugin`.

For normal installation and updates, use the
[ISEE marketplace](https://github.com/suuus/isee-plugins).
