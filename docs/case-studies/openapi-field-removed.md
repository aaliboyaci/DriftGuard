# Case Study: OpenAPI Response Field Removed

## Scenario

A backend team removes the `tag` field from the `GET /pets/{id}` response to simplify the API. The mobile app uses `tag` to display pet categories.

## Baseline (v1)

```json
{
  "id": 1,
  "name": "Buddy",
  "status": "available",
  "tag": "golden-retriever"
}
```

## Current (v2)

```json
{
  "id": 1,
  "name": "Buddy",
  "status": "available"
}
```

## DriftGuard Output

```
Severity   | Resource | Change                          | Reason
-----------+----------+---------------------------------+----------------------------------
[X]        | Pet      | Field removed: Pet.tag (string) | Consumers expecting this field
BREAKING   |          |                                 | will fail
```

## Why This Breaks Production

- The mobile app reads `response.tag` and displays it in the UI
- After the field is removed, `response.tag` returns `undefined`/`null`
- The app crashes or shows empty content where the tag should be
- This isn't caught by backend tests because they don't test the mobile contract

## How DriftGuard Catches It

```bash
driftguard snapshot --name v1    # before the change
driftguard snapshot --name v2    # after the change
driftguard check -b v1 -c v2    # exits 1: BREAKING CHANGE
```

The CI pipeline fails before the change reaches production.
