# Writing a New Adapter

DriftGuard uses the adapter pattern for schema collection. Adding support for a new data source requires implementing a single interface.

## Interface

```python
from driftguard.collectors.base import BaseCollector
from driftguard.schema.models import ResourceSchema


class MyCollector(BaseCollector):
    def __init__(self, connection_string: str) -> None:
        self._conn = connection_string

    @property
    def name(self) -> str:
        return "my-source"

    def collect(self) -> list[ResourceSchema]:
        # 1. Connect to source
        # 2. Extract raw schema
        # 3. Normalize to ResourceSchema with FieldDef list
        # 4. Return list of ResourceSchema
        ...
```

## Steps

### 1. Create the collector

Create `src/driftguard/collectors/my_collector.py`:

```python
from driftguard.collectors.base import BaseCollector
from driftguard.schema.models import FieldDef, ResourceSchema, SourceType


class MyCollector(BaseCollector):
    def __init__(self, connection: str) -> None:
        self._connection = connection

    @property
    def name(self) -> str:
        return f"my-source:{self._connection}"

    def collect(self) -> list[ResourceSchema]:
        # Connect and extract schemas
        raw_schemas = self._fetch_schemas()

        resources = []
        for schema_name, fields_data in raw_schemas.items():
            fields = [
                FieldDef(
                    name=f["name"],
                    field_type=self._normalize_type(f["type"]),
                    nullable=f.get("nullable", False),
                    required=f.get("required", True),
                )
                for f in fields_data
            ]
            resources.append(
                ResourceSchema(
                    name=schema_name,
                    source_type=SourceType.JSON_SCHEMA,  # or add a new SourceType
                    fields=fields,
                )
            )
        return resources
```

### 2. Add the SourceType (if new)

Add to `src/driftguard/schema/models.py`:

```python
class SourceType(str, Enum):
    # existing types...
    MY_SOURCE = "my_source"
```

### 3. Register in CLI

Update `src/driftguard/cli/app.py` in `_create_collector()`:

```python
case SourceType.MY_SOURCE:
    return MyCollector(source.connection)
```

### 4. Export from __init__.py

Update `src/driftguard/collectors/__init__.py`:

```python
from driftguard.collectors.my_collector import MyCollector
```

### 5. Write tests

Create `tests/unit/test_my_collector.py` with:
- Test fixture files (if file-based source)
- Test that `collect()` returns correct `ResourceSchema` list
- Test field type normalization
- Test nullable/required detection
- Test edge cases (empty source, missing fields)

## Type Normalization

All collectors must normalize source types to these standard types:

| Normalized Type | Examples |
|-----------------|----------|
| `string` | VARCHAR, TEXT, UUID, DATE, TIMESTAMP |
| `integer` | INT, BIGINT, SMALLINT, SERIAL |
| `number` | FLOAT, DECIMAL, NUMERIC, REAL |
| `boolean` | BOOL, BOOLEAN |
| `array` | ARRAY, list |
| `object` | JSON, JSONB, nested object |
| `null` | NULL, None |
