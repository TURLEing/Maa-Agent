# Initialize your roster

Log into the intended account and ensure no other MAA task is running. Clear all
operator filters before scanning. The first release exposes the steps separately;
a single initialize-roster command and automatic account binding are not implemented.

From the checkout root, using your configured maa-cli:

```powershell
New-Item -ItemType Directory -Force debug | Out-Null
maa run "$((Get-Location).Path)/tasks/scan-operators.json" --batch -vv --log-file=./debug/operators-new.log
.venv\Scripts\python.exe scripts/operator_roster.py refresh-catalog
.venv\Scripts\python.exe scripts/operator_roster.py import-scan debug/operators-new.log
.venv\Scripts\python.exe scripts/operator_roster.py query OPERATOR_NAME
```

For macOS, use the equivalent Bash commands in [macOS deployment](macos.md#首次干员扫描).
Pass an absolute task path: maa-cli resolves relative paths under its own config
directory, not the current checkout.

The catalog is downloaded from PRTS. Its content remains upstream material.
Import accepts a complete scan and rejects reduced coverage. Results are local:
data/accounts/current/{roster,elite2,scan}.json. Review counts before using them.
All owned operators are retained, not only elite-two operators.

Keep separate checkouts/data backups for different accounts in this alpha; the
script currently uses a single current account directory. Do not overwrite one
account's roster with another account. Skills, masteries and modules are not scanned.
