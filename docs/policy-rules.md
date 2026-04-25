# Policy Rules

DriftGuard classifies every schema change into one of three severity levels.

## Severity Levels

| Level | Meaning | CI Behavior |
|-------|---------|-------------|
| **Breaking** | Will likely break consumers | Exit code 1 (CI fails) |
| **Warning** | May break some consumers | Reported but CI passes |
| **Info** | Backward compatible | Reported for visibility |

## Default Rules

### Breaking Changes

| Change | Reason |
|--------|--------|
| Field removed | Consumers expecting this field will fail |
| Required field added | Existing producers/consumers may not provide it |
| Field renamed | Effectively a remove + add |
| Type narrowing (string → integer) | Parse and validation behavior changes |
| Enum values removed | Existing data with removed values becomes invalid |
| Optional → required | Existing data without this field fails validation |
| Resource removed | All consumers depending on this resource break |

### Warnings

| Change | Reason |
|--------|--------|
| Type widening (integer → number) | Some consumers may accept, others may not |
| Type widening (integer → string) | Serialization may change |
| Nullable false → true | Consumers without null handling may fail |
| Nullable true → false | Existing null values will cause errors |
| Enum values added | Strict enum consumers may not handle new values |

### Info

| Change | Reason |
|--------|--------|
| Optional field added | Backward compatible |
| Required → optional | Backward compatible |
| Resource added | No existing consumers affected |

## Type Widening Transitions

These type changes are treated as **warnings** instead of breaking:

```
integer → number
integer → string
number  → string
boolean → string
```

Any other type change is treated as **breaking**.

## Policy Overrides

You can override default severity in `driftguard.yaml`:

```yaml
policy_overrides:
  - resource: "legacy_*"
    category: field_removed
    severity: warning    # Downgrade from breaking

  - resource: "internal_*"
    category: type_changed
    severity: info       # Downgrade from breaking/warning
```

Override fields:
- `resource` - Resource name pattern
- `field` - Field name pattern
- `category` - Change category to match
- `severity` - Override severity: `breaking`, `warning`, `info`, `ignore`
