# Architecture

## Project Structure

```
dt-terraform-example/
├── pipelines/                      # NEW — Export/Deploy pipeline system
│   ├── export.py                   # Export CLI entry point
│   ├── deploy.py                   # Deploy CLI entry point
│   ├── core/                       # Shared utilities
│   │   ├── config.py               # pipeline.yaml + .env loader
│   │   ├── dt_client.py            # Dynatrace API client
│   │   ├── logging_setup.py        # Consistent logging
│   │   └── types.py                # Data classes, enums, API mappings
│   ├── export_pipeline/            # Export-specific modules
│   │   ├── exporter.py             # Export orchestrator
│   │   ├── format_terraform.py     # .tf.json generator
│   │   ├── format_monaco.py        # Monaco v2 structure generator
│   │   ├── reconciliation.py       # Compare export vs tenant state
│   │   └── topology.py             # Dependency graph analysis
│   └── deploy_pipeline/            # Deploy-specific modules
│       ├── deployer.py             # Deploy orchestrator
│       ├── format_detector.py      # Auto-detect: terraform vs monaco
│       ├── deploy_terraform.py     # terraform init/plan/apply
│       ├── deploy_monaco.py        # monaco deploy
│       └── results_analyzer.py     # Post-deploy analysis
│
├── .github/workflows/              # GitHub Actions
│   ├── export.yml                  # Export workflow (workflow_dispatch)
│   └── deploy.yml                  # Deploy workflow (workflow_dispatch)
│
├── scripts/                        # Legacy single-step migration tools
│   ├── migrate.py
│   ├── migrate.sh
│   ├── clone-config.sh
│   └── verify_migration.py
│
├── config/
│   ├── .env.example                # Environment variable template
│   ├── environments.yaml           # Tenant configuration template
│   └── pipeline.yaml.example       # Pipeline behavior configuration
│
├── docs/
│   ├── GETTING_STARTED.md
│   ├── ADVANCED.md
│   └── TROUBLESHOOTING.md
│
├── .claude/                        # AI assistant instructions
├── README.md
├── CHANGELOG.md
├── setup.sh
├── requirements.txt
└── .gitignore
```

## Pipeline Architecture

![Pipeline Overview](../docs/diagrams/pipeline-overview.svg)

### Export Pipeline
```
Source Tenant
    ↓
[1] Verify API connection
    ↓
[2] Export raw JSON via Dynatrace API
    ↓
[3] Transform to format ─┬─ Terraform (.tf.json)
                         └─ Monaco (manifest.yaml + config.yaml)
    ↓
[4] Reconciliation: compare export vs tenant counts
    ↓
[5] Topology: map entity cross-references, compute deploy order
    ↓
[6] Push to GitHub branch → Open PR for review
```

### Deploy Pipeline
```
GitHub branch (or local dir)
    ↓
[1] Auto-detect format (terraform / monaco / unknown)
    ↓
[2] Verify target tenant connection
    ↓
[3] Snapshot pre-deploy state (counts)
    ↓
[4] Deploy ─┬─ terraform init → plan → apply
             └─ monaco deploy
    ↓
[5] Post-deploy analysis: compare before/after counts
```

### Git as Intermediary
```
Export Pipeline ──→ GitHub branch ──→ PR Review ──→ Deploy Pipeline
                        ↑                              ↓
                   Code review               Target Tenant
                   Topology analysis
```

## Legacy Migration Tools

The `scripts/` directory contains the original single-step migration tools
that combine export and deploy into one operation. These are preserved for
quick migrations but the pipeline system is preferred for production use.

```
scripts/migrate.py   ← All-in-one: backup → download → validate → deploy
scripts/migrate.sh   ← Shell equivalent
scripts/clone-config.sh  ← Download config to timestamped dir
scripts/verify_migration.py  ← Compare source/target counts
setup.sh             ← Interactive setup wizard
```

## Technology Decisions

See `DECISIONS.md` for why we chose:
- Two-pipeline architecture (export/deploy separated by git)
- GitHub Actions for CI/CD orchestration
- Dual format support (Terraform + Monaco)
- .tf.json format (Terraform JSON syntax, avoids HCL string formatting)
