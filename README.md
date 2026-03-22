# LoanLens

LoanLens is a local CLI for tracking a home loan, generating repayment schedules, modelling OD-linked savings, recording payments, and running prepayment or rate-change simulations.

This README reflects the current implemented state of the utility in this repository, not the aspirational PRD end-state.

## Installation

Development setup:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

Run commands with either the installed `loanlens` entrypoint or:

```bash
.venv/bin/python -m loanlens --help
```

## First Run

LoanLens expects a config file under `~/.loanlens/config.json` by default.

On first run:

- interactive use: run `loanlens wizard run`
- non-interactive use: run `loanlens --yes loan list`

The global `--yes` flag writes a default config if one does not exist. This matters in CI, tests, and any non-TTY environment.

## Getting Started

First-time interactive flow:

1. Create the config:

```bash
loanlens wizard run
```

2. Add your first loan:

```bash
loanlens loan add
```

This command prompts for the loan details, including:

- loan name
- bank name
- account number
- sanction amount
- disbursed amount
- disbursement date
- interest rate
- tenure
- EMI start date
- EMI day

It can also capture an initial moratorium during loan creation. In interactive mode, `loan add` now asks whether the loan has a moratorium. If you answer yes, it will collect:

- moratorium start date
- moratorium end date
- moratorium type:
  `INTEREST_CAPITALISE`, `INTEREST_DEFER`, or `FULL_DEFER`

3. List loans and copy the generated `loan_id`:

```bash
loanlens loan list
```

4. Generate and inspect the repayment schedule:

```bash
loanlens schedule regenerate <loan_id>
loanlens schedule show <loan_id>
```

5. View summary outputs:

```bash
loanlens dashboard <loan_id>
loanlens amortize summary <loan_id>
loanlens emi show <loan_id>
```

6. Start recording activity as it happens:

```bash
loanlens payment record <loan_id> 44186 --date 2024-05-05
loanlens od deposit <loan_id> 500000 --date 2024-05-01
loanlens rate add <loan_id> --roi 9.25 --date 2025-05-05
```

If the moratorium was not captured during `loan add`, you can still add it later:

```bash
loanlens moratorium add <loan_id> --from 2024-07-05 --to 2024-08-05 --type INTEREST_CAPITALISE
loanlens moratorium list <loan_id>
loanlens schedule regenerate <loan_id>
loanlens moratorium impact <loan_id> <moratorium_id>
```

7. Run scenario analysis:

```bash
loanlens simulate prepay <loan_id> 200000 --date 2024-10-05
loanlens simulate compare <loan_id> 200000 --date 2024-10-05 --roi 8
```

8. Generate annual interest output or exports:

```bash
loanlens cert interest <loan_id> --fy 2025-26
loanlens export csv <loan_id> schedule.csv
```

Non-interactive first-time flow:

1. Create a default config without prompts:

```bash
loanlens --yes loan list
```

2. Add a loan by passing all required options to `loan add`. Example:

```bash
loanlens --yes loan add \
  --name "SBI Home Loan" \
  --bank-name "SBI" \
  --account-number "SBI12345678" \
  --sanction-amount 5000000 \
  --disbursed-amount 5000000 \
  --disbursement-date 2024-04-01 \
  --roi-initial 8.75 \
  --roi-type FLOATING \
  --tenure-months 240 \
  --emi-start-date 2024-05-01 \
  --emi-day 5 \
  --adjustment-mode ADJUST_EMI \
  --prepayment-charges-pct 0 \
  --emi-rounding rupee
```

3. If the loan already has a moratorium and you want to capture it at creation time, add:

```bash
  --moratorium \
  --moratorium-from 2024-07-05 \
  --moratorium-to 2024-08-05 \
  --moratorium-type INTEREST_CAPITALISE
```

## Global Flags

- `--json` outputs machine-readable JSON
- `--no-color` disables Rich styling
- `--yes` skips first-run config prompting and uses defaults where supported
- `--loan / -l` sets an active loan context value in the app state

## What Works Now

Implemented command groups:

- `loan`: add, list, show, edit, archive
- `emi`: calculate, show
- `schedule`: show, export, regenerate
- `amortize`: show, summary, chart
- `moratorium`: add, list, impact
- `od`: deposit, withdraw, balance, history, impact
- `rate`: add, list, impact
- `simulate`: prepay, compare, recurring, rate-change, save, list, show
- `payment`: record, list, reconcile
- `dashboard`
- `cert interest`
- `config`: show, set
- `backup`: create, list, restore
- `export`: csv, pdf, markdown
- `wizard run`

## Usage Notes

Some commands prompt for values if required options are omitted. The most important ones:

- `loan add` prompts for the loan fields and can optionally prompt for moratorium details
- `emi calculate` prompts for principal, rate, tenure, and rounding
- `wizard run` prompts for config defaults unless `--yes` is set globally

Most other implemented commands are argument-driven. Examples:

```bash
loanlens loan list
loanlens loan show <loan_id>
loanlens emi show <loan_id>
loanlens schedule regenerate <loan_id>
loanlens schedule show <loan_id>
loanlens amortize summary <loan_id>
loanlens moratorium add <loan_id> --from 2024-07-05 --to 2024-08-05 --type INTEREST_CAPITALISE
loanlens od deposit <loan_id> 500000 --date 2024-05-01
loanlens rate add <loan_id> --roi 9.25 --date 2025-05-05
loanlens simulate prepay <loan_id> 200000 --date 2024-10-05
loanlens payment record <loan_id> 44186 --date 2024-05-05
loanlens cert interest <loan_id> --fy 2025-26
```

## Data Location

Default paths:

- config: `~/.loanlens/config.json`
- JSON store: `~/.loanlens/data.json`
- SQLite store: `~/.loanlens/loanlens.db`
- backups: `~/.loanlens/backups/`

`LOANLENS_DATA_DIR` overrides the base data directory.

## Backend Notes

- JSON is the default backend.
- SQLite is implemented and can be selected with `loanlens config set storage_backend sqlite`.
- Backup commands are currently most meaningful for the JSON backend because they operate on the JSON data file path.

## Export Notes

- CSV export writes schedule rows via pandas.
- Markdown export writes a simple markdown table.
- PDF export currently degrades to a simple text-file write after checking for `reportlab`; it is not a formatted PDF report yet.

## Verification Status

Current repository verification:

- `pytest tests/ -q`
- `ruff check loanlens tests`
- `mypy --strict loanlens`
- engine coverage: 96% via `pytest --cov=loanlens.engine --cov-report=term-missing tests/unit/engine`

## Specification

The authoritative product specification remains [`LoanLens_PRD.md`](/home/aditya/codebase/loanlens/LoanLens_PRD.md), but some features in the PRD are still implemented pragmatically rather than with full UX polish.
