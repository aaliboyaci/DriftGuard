# Architecture

DriftGuard is designed as a modular pipeline. Each layer has a single responsibility and communicates through well-defined models.

## Pipeline Overview

```
Data Sources ──> Collectors ──> Normalizer ──> Snapshot Store
                                                     │
                                              Diff Engine
                                                     │
                                             Policy Engine
                                                     │
                                         Reporters / CI Gate
```

## Layers

### CLI (`driftguard.cli`)
Entry point for all user interactions. Built with Typer for type-safe argument parsing and Rich for terminal output.

**Commands:** `init`, `snapshot`, `diff`, `check`, `report`

### Config (`driftguard.config`)
Handles `driftguard.yaml` parsing and validation using Pydantic v2. Defines which sources to monitor and any policy overrides.

### Collectors (`driftguard.collectors`)
Source adapters that extract raw schemas and normalize them into the internal model. Each collector implements `BaseCollector.collect() -> list[ResourceSchema]`.

| Collector | Source | Strategy |
|-----------|--------|----------|
| `PostgresCollector` | PostgreSQL | SQLAlchemy `inspect()` on information_schema |
| `OpenApiCollector` | OpenAPI 3.x / Swagger 2.x | Parse component schemas from YAML/JSON |
| `JsonSchemaCollector` | JSON Schema | Extract properties with type/nullable/enum |
| `CsvCollector` | CSV files | Read headers, infer types from sample rows |

### Schema (`driftguard.schema`)
The normalized internal model. All collectors produce these types regardless of source.

- **`ContractSnapshot`** - Point-in-time collection of all resource schemas
- **`ResourceSchema`** - Single table, endpoint, topic, or file schema
- **`FieldDef`** - Field metadata: name, type, nullable, required, enum, constraints

### Diff Engine (`driftguard.diff`)
Compares two `ContractSnapshot`s and produces semantic `DiffEvent`s. This is not text diff — each event describes what changed at the field/resource level.

**Event types:** `FieldAdded`, `FieldRemoved`, `TypeChanged`, `NullableChanged`, `RequiredChanged`, `EnumValuesChanged`, `ResourceAdded`, `ResourceRemoved`

### Policy Engine (`driftguard.policy`)
Evaluates each `DiffEvent` against risk rules and produces a `PolicyDecision` with severity level.

**Key rules:**
- Type widening (int→number, int→string) = Warning
- Type narrowing (string→integer) = Breaking
- Field removed = Breaking
- Required field added = Breaking
- Enum values removed = Breaking
- Nullable changed = Warning

### Reporters (`driftguard.reporters`)
Generate output in various formats from diff and policy results.

| Reporter | Format | Use Case |
|----------|--------|----------|
| `TerminalReporter` | Rich tables | Local development |
| `JsonReporter` | JSON | Machine consumption, CI integration |
| `MarkdownReporter` | Markdown | PR comments, CI artifacts |
| `HtmlReporter` | HTML | Standalone reports |

### Store (`driftguard.store`)
Versioned snapshot persistence. Currently file-based (JSON), designed for future S3/Git backends.

## Adding New Components

### New Collector
1. Create a class extending `BaseCollector` in `driftguard/collectors/`
2. Implement `collect() -> list[ResourceSchema]` and `name` property
3. Register in `cli/app.py:_create_collector()`
4. Add tests with fixture files

### New Reporter
1. Create a class in `driftguard/reporters/`
2. Implement `render(diff_result, policy_result) -> str`
3. Register in `cli/app.py:_generate_report()`
