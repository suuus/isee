# Contributing

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m build
```

Keep orchestration fail-closed. ISEE must not reproduce profile validation in
prompts or convert missing tools into success.
