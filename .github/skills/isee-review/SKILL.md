---
name: isee-review
description: Compare AERP Evidence with an ISEE execution manifest and route material differences to review.
---

# Review Evidence

Run:

```bash
isee evaluate --manifest <manifest> --evidence <record-or-bundle>
```

Report missing Intent or Structure bindings and unsatisfied Evidence
requirements. Do not edit immutable ADRP, ASRP, or AERP records to make the
evaluation pass.
