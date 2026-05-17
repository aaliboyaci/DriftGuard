# Public API Surface

## Stable (v1.0.0)

These modules and classes are part of the public API. Breaking changes will follow semver.

### Schema Models (`driftguard.schema`)
- `ContractSnapshot` — top-level snapshot model
- `ResourceSchema` — single resource (table/endpoint/file)
- `FieldDef` — field definition with constraints
- `FieldConstraint` — constraint metadata
- `SourceType` — enum of supported source types
- `NestedContract`, `NestedResource`, `NestedField` — nested/JSONB models
- `NestedFieldType` — nested field type enum

### Diff Engine (`driftguard.diff`)
- `compute_diff(baseline, current)` → `DiffResult`
- `compute_openapi_diff(baseline, current)` → `DiffResult`
- `compute_nested_diff(baseline, current)` → `DiffResult`
- `DiffResult` — result container with events
- All `DiffEvent` subclasses

### Policy Engine (`driftguard.policy`)
- `evaluate(diff_result, mode=DEFAULT)` → `PolicyResult`
- `PolicyResult`, `PolicyDecision`, `Severity`, `PolicyMode`
- `SuppressionFile`, `SuppressionRule`
- `WaiverStore`, `Waiver`

### Reporters (`driftguard.reporters`)
- `TerminalReporter`, `JsonReporter`, `MarkdownReporter`, `HtmlReporter`, `PrCommentReporter`

### Store (`driftguard.store`)
- `SnapshotBackend` — abstract interface
- `LocalStore` — filesystem backend
- `S3Backend` — S3-compatible backend
- `SnapshotRegistry` — branch-aware discovery

### Registry (`driftguard.registry`)
- `ContractRegistry` — publish/pull/impact analysis
- `ServiceMetadata`, `ServiceDependency`, `RegistryConfig`

### Inference (`driftguard.inference`)
- `infer_shape(samples, ...)` → `NestedResource`
- `InferenceConfig`

### Collectors (`driftguard.collectors`)
- `OpenApiCollector`, `JsonSchemaCollector`, `CsvCollector`
- `PostgresCollector`, `MysqlCollector`, `SqliteCollector`
- `JsonSampleCollector`, `PostgresJsonbCollector`
- `SequelizeCollector`, `PrismaCollector`
- `YamlCollector`

### CLI
- `driftguard init/snapshot/diff/check/report`
- `driftguard openapi diff`
- `driftguard nested infer/diff`
- `driftguard config validate/print`
- `driftguard snapshots list/show/delete`
- `driftguard demo`

## Internal (not public API)
- `driftguard.diff.engine._diff_field`, `_diff_resource`, `_detect_renames`
- `driftguard.collectors.json_collector._extract_fields_from_schema`
- `driftguard.inference.json_shape._PathAccumulator`
- `driftguard.collectors.openapi_extractor._resolve_ref`
- Any function/class prefixed with `_`
