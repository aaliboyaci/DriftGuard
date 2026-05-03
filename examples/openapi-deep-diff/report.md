# Schema Drift Report

**Baseline:** Pet Store API 1.0.0  
**Current:** Pet Store API 2.0.0  

## Summary

| Metric | Count |
|--------|-------|
| Total changes | 13 |
| Breaking | 10 |
| Warning | 2 |
| Info | 1 |

## Changes

| Severity | Resource | Change | Reason |
|----------|----------|--------|--------|
| **BREAKING** | /owners | Path removed: /owners | API path removed; all consumers of this endpoint will fail |
| **INFO** | /health | Path added: /health | New API path added; backward compatible |
| **BREAKING** | GET /pets | Parameter added: GET /pets header param 'X-Api-Key' (required) | Required header parameter 'X-Api-Key' added; existing clients will fail |
| **BREAKING** | GET /pets | Parameter changed: GET /pets query param 'status' (required: False -> True) | Parameter 'status' became required; existing clients will fail |
| **BREAKING** | GET /pets | Response status removed: GET /pets 400 | Response status code removed; clients handling this status will break |
| **BREAKING** | GET /pets 200 response | Response field removed: GET /pets 200 'tag' (string) | Consumers expecting this field will fail |
| **BREAKING** | POST /pets request | Request field added: POST /pets body 'category' (string) (required) | Adding a required field may break existing producers/consumers |
| **BREAKING** | POST /pets request | Request field removed: POST /pets body 'tag' (string) | Consumers expecting this field will fail |
| **BREAKING** | POST /pets 201 response | Response field removed: POST /pets 201 'tag' (string) | Consumers expecting this field will fail |
| **BREAKING** | DELETE /pets/{petId} | Method removed: DELETE /pets/{petId} | HTTP method removed; clients using this method will get 405 |
| **WARNING** | GET /pets/{petId} | Endpoint deprecated: GET /pets/{petId} | Endpoint marked as deprecated; plan migration before removal |
| **WARNING** | GET /pets/{petId} | Parameter changed: GET /pets/{petId} path param 'petId' (type: integer -> string) | Parameter 'petId' changed (type: integer -> string) |
| **BREAKING** | GET /pets/{petId} 200 response | Response field removed: GET /pets/{petId} 200 'tag' (string) | Consumers expecting this field will fail |
