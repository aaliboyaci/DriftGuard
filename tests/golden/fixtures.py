"""Golden test fixtures - predefined baseline/current snapshot pairs with expected results."""

from driftguard.schema.models import (
    ContractSnapshot,
    FieldConstraint,
    FieldDef,
    ResourceSchema,
    SourceType,
)


def baseline_snapshot() -> ContractSnapshot:
    """Standard baseline snapshot for golden tests."""
    return ContractSnapshot(
        name="baseline",
        resources=[
            ResourceSchema(
                name="customers",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=True)),
                    FieldDef(name="name", field_type="string"),
                    FieldDef(name="email", field_type="string"),
                    FieldDef(name="age", field_type="integer", nullable=True, required=False),
                    FieldDef(
                        name="status",
                        field_type="string",
                        enum_values=["active", "inactive"],
                    ),
                ],
            ),
            ResourceSchema(
                name="orders",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=True)),
                    FieldDef(name="customer_id", field_type="integer"),
                    FieldDef(name="amount", field_type="integer"),
                    FieldDef(name="currency", field_type="string"),
                ],
            ),
            ResourceSchema(
                name="legacy_reports",
                source_type=SourceType.CSV,
                fields=[
                    FieldDef(name="report_id", field_type="string"),
                    FieldDef(name="data", field_type="string"),
                ],
            ),
        ],
    )


def current_snapshot_breaking() -> ContractSnapshot:
    """Current snapshot with multiple breaking changes."""
    return ContractSnapshot(
        name="current",
        resources=[
            ResourceSchema(
                name="customers",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=True)),
                    FieldDef(name="name", field_type="string"),
                    # email removed -> breaking
                    FieldDef(name="age", field_type="string", nullable=True, required=False),  # integer->string: breaking
                    FieldDef(
                        name="status",
                        field_type="string",
                        enum_values=["active", "inactive", "banned"],  # enum added: warning
                    ),
                    FieldDef(name="phone", field_type="string", required=True),  # required field added: breaking
                ],
            ),
            ResourceSchema(
                name="orders",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=True)),
                    FieldDef(name="customer_id", field_type="integer"),
                    FieldDef(name="amount", field_type="number"),  # integer->number: warning (widening)
                    FieldDef(name="currency", field_type="string", nullable=True),  # nullable changed: warning
                ],
            ),
            # legacy_reports removed -> breaking
            ResourceSchema(
                name="payments",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer"),
                    FieldDef(name="order_id", field_type="integer"),
                ],
            ),  # new resource -> info
        ],
    )


def current_snapshot_clean() -> ContractSnapshot:
    """Current snapshot with only backward-compatible changes."""
    return ContractSnapshot(
        name="current-clean",
        resources=[
            ResourceSchema(
                name="customers",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=True)),
                    FieldDef(name="name", field_type="string"),
                    FieldDef(name="email", field_type="string"),
                    FieldDef(name="age", field_type="integer", nullable=True, required=False),
                    FieldDef(
                        name="status",
                        field_type="string",
                        enum_values=["active", "inactive"],
                    ),
                    FieldDef(name="phone", field_type="string", required=False),  # optional add -> info
                ],
            ),
            ResourceSchema(
                name="orders",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer", constraints=FieldConstraint(primary_key=True)),
                    FieldDef(name="customer_id", field_type="integer"),
                    FieldDef(name="amount", field_type="integer"),
                    FieldDef(name="currency", field_type="string"),
                ],
            ),
            ResourceSchema(
                name="legacy_reports",
                source_type=SourceType.CSV,
                fields=[
                    FieldDef(name="report_id", field_type="string"),
                    FieldDef(name="data", field_type="string"),
                ],
            ),
        ],
    )
