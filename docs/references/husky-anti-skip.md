# Husky Anti-Skip Implementation

To prevent bypassing quality gates (unit tests), the pre-commit hook is configured to fail on errors and explicitly warn against using `--no-verify`.

## Configuration in `.husky/pre-commit`
```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

echo " [Husky] 執行預選檢查... ⚠️ 禁止使用 --no-verify 跳過測試。有錯誤務必修復或回報給使用者 ⚠️"
npm test
```

## Rationale
In AI-assisted development, agents might be tempted to skip verification if environment paths are broken. Enforcing `npm test` ensures that the agent fixes the environment (e.g., recreating the `venv`) rather than pushing broken code.
