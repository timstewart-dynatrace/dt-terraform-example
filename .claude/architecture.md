# Architecture

## Project Structure

```
dt-terraform-example/
├── scripts/
│   ├── migrate.py              # Python migration implementation
│   ├── migrate.sh              # Shell migration implementation
│   ├── clone-config.sh         # Clone configuration helper
│   └── verify_migration.py     # Post-migration validation
│
├── config/
│   ├── .env.example            # Environment variable template
│   └── environments.yaml       # Terraform environment configuration
│
├── docs/
│   ├── GETTING_STARTED.md      # Quick-start guide
│   ├── ADVANCED.md             # Advanced usage and CI/CD integration
│   └── TROUBLESHOOTING.md      # Common issues and solutions
│
├── .claude/                    # AI assistant instructions
│   ├── CLAUDE.md
│   ├── DECISIONS.md
│   ├── architecture.md
│   ├── settings.json
│   ├── phases/
│   └── rules/
│
├── README.md
├── CHANGELOG.md
├── setup.sh                    # Interactive setup wizard
├── requirements.txt            # Python dependencies
└── .gitignore
```

## Key Components

```
Terraform Migration Tools (Python + Shell implementations)
  │
  ├── scripts/migrate.py         ← Python: argparse CLI, .env loading, logging
  ├── scripts/migrate.sh         ← Bash: colored output, error handling
  │     │
  │     ├── 1. Verify Prerequisites (Terraform CLI, tokens, connectivity)
  │     ├── 2. Backup Target Tenant (download current config)
  │     ├── 3. Download Source Config (export into Terraform-compatible structure)
  │     ├── 4. Validate Configuration (YAML checks, schema validation)
  │     └── 5. Deploy to Target (apply config, with dry-run option)
  │
  ├── scripts/clone-config.sh    ← Downloads tenant config into timestamped folders
  │
  ├── scripts/verify_migration.py ← Compares source/target counts, pass/warn/fail
  │
  └── setup.sh                   ← Interactive wizard: check deps, collect URLs/tokens, write .env
```

## Data Flow

### Full Tenant Migration
```
Source Tenant → API Export → Local YAML Config → Validation → API Deploy → Target Tenant
                                                                  ↑
                                                        Backup of target
                                                        saved first
```

### Clone Configuration
```
Source Tenant → API Download → Timestamped Local Directory
```

### Verify Migration
```
Source Tenant ─┐
               ├── Compare Counts → Pass/Warn/Fail Report
Target Tenant ─┘
```

## Technology Decisions

See `DECISIONS.md` for why we chose:
- Dual Python/Shell implementations
- Terraform-compatible workflow structure
- Backup-first deployment behavior
