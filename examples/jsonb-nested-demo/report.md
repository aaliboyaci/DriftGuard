# Schema Drift Report

**Baseline:** work_orders  
**Current:** work_orders  

## Summary

| Metric | Count |
|--------|-------|
| Total changes | 12 |
| Breaking | 11 |
| Warning | 1 |
| Info | 0 |

## Changes

| Severity | Resource | Change | Reason |
|----------|----------|--------|--------|
| **BREAKING** | work_orders | Nested field removed: work_orders.machine.location (string) | Nested field 'machine.location' removed with high confidence (1.0); consumers will break |
| **WARNING** | work_orders | Nested field removed: work_orders.metadata.notes (string) | Nested field 'metadata.notes' removed with low confidence (0.3333); may be intermittent |
| **BREAKING** | work_orders | Nested field removed: work_orders.steps[].required (boolean) | Nested field 'steps[].required' removed with high confidence (1.0); consumers will break |
| **BREAKING** | work_orders | Nested field removed: work_orders.steps[].timeout (integer) | Nested field 'steps[].timeout' removed with high confidence (1.0); consumers will break |
| **BREAKING** | work_orders | Nested field added: work_orders.assignee (string) (required) | Required nested field 'assignee' added with high confidence; existing producers may not provide it |
| **BREAKING** | work_orders | Nested field added: work_orders.metadata.version (integer) (required) | Required nested field 'metadata.version' added with high confidence; existing producers may not provide it |
| **BREAKING** | work_orders | Nested field added: work_orders.steps[].mandatory (boolean) (required) | Required nested field 'steps[].mandatory' added with high confidence; existing producers may not provide it |
| **BREAKING** | work_orders | Nested enum values changed: work_orders.machine.id (+['MCH-103'], -['MCH-102']) | Nested enum values removed from 'machine.id': MCH-102; existing data may be invalid |
| **BREAKING** | work_orders | Nested enum values changed: work_orders.machine.status (+['maintenance'], -['idle']) | Nested enum values removed from 'machine.status': idle; existing data may be invalid |
| **BREAKING** | work_orders | Nested enum values changed: work_orders.metadata.priority (+[], -['low']) | Nested enum values removed from 'metadata.priority': low; existing data may be invalid |
| **BREAKING** | work_orders | Nested enum values changed: work_orders.steps[].operationId (+['OP-INSPECT'], -['OP-DRILL', 'OP-PAINT']) | Nested enum values removed from 'steps[].operationId': OP-DRILL, OP-PAINT; existing data may be invalid |
| **BREAKING** | work_orders | Nested enum values changed: work_orders.workOrderId (+['WO-2024-004', 'WO-2024-005'], -['WO-2024-001', 'WO-2024-002', 'WO-2024-003']) | Nested enum values removed from 'workOrderId': WO-2024-001, WO-2024-002, WO-2024-003; existing data may be invalid |
