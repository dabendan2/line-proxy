# LINE Proxy Path Migration & ENOENT Troubleshooting

## Context
In May 2026, the `line-proxy` project was moved from the hermes-internal directory (`~/.hermes/scripts/line-proxy`) to the home directory (`~/line-proxy`) for better visibility and management.

## Symptom
`mcporter` fails with an `ENOENT` error when calling `line_proxy` tools:
```
[mcporter] line_proxy appears offline (spawn /home/ubuntu/.hermes/scripts/line-proxy/venv/bin/python3 ENOENT).
Error: spawn /home/ubuntu/.hermes/scripts/line-proxy/venv/bin/python3 ENOENT
```

## Diagnosis
The `mcporter` configuration is pointing to the old path. `mcporter` might be reading from multiple locations:
1. `~/line-proxy/config/mcporter.json`
2. `~/config/mcporter.json`

## Fix
1. Locate the active `mcporter.json` (e.g., `find ~ -name "mcporter.json"`).
2. Update the `command` and `args` paths to use the new `~/line-proxy/` prefix.
3. Verify with `mcporter list --json` to ensure the transport path is correct.
