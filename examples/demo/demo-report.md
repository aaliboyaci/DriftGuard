# Schema Drift Report

**Baseline:** baseline  
**Current:** current  

## Summary

| Metric | Count |
|--------|-------|
| Total changes | 5 |
| Breaking | 2 |
| Warning | 2 |
| Info | 1 |

## Changes

| Severity | Resource | Change | Reason |
|----------|----------|--------|--------|
| **INFO** | Owner | Field added: Owner.address (string) | Adding an optional field is backward compatible |
| **WARNING** | Owner | Type changed: Owner.id (integer -> string) | Type widened from integer to string; some consumers may accept this |
| **BREAKING** | Pet | Field removed: Pet.tag (string) | Consumers expecting this field will fail |
| **BREAKING** | Pet | Field added: Pet.category (string) | Adding a required field may break existing producers/consumers |
| **WARNING** | Pet | Enum values changed: Pet.status | Enum values added: archived; strict consumers may not handle new values |
