# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability in DriftGuard, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email the maintainer directly or use [GitHub's private vulnerability reporting](https://github.com/aaliboyaci/DriftGuard/security/advisories/new)
3. Include a description of the vulnerability, steps to reproduce, and potential impact

We will acknowledge receipt within 48 hours and aim to provide a fix within 7 days for critical issues.

## Security Considerations

DriftGuard handles database connection strings and API endpoints in its configuration. Keep in mind:

- **Never commit** `driftguard.yaml` with production credentials to public repositories
- Use environment variables or secret managers for sensitive connection strings
- The `.driftguard/` directory may contain snapshot data — review before sharing
- Snapshot files are plain JSON and may contain schema metadata (table names, column names, types)

## Dependencies

We regularly update dependencies and monitor for known vulnerabilities. If you notice an outdated dependency with a known CVE, please open an issue.
