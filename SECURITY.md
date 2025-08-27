# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Reporting a Vulnerability

Please report (suspected) security vulnerabilities to the maintainers via GitHub Issues or directly via email. You will receive a response from us within 48 hours. If the issue is confirmed, we will release a patch as soon as possible depending on complexity but historically within a few days.

### Guidelines

- Please do not open GitHub Issues for security vulnerabilities until we have had a chance to review and address them
- Provide as much detail as possible including:
  - Description of the vulnerability
  - Steps to reproduce
  - Potential impact
  - Suggested fix (if any)

## Security Best Practices

When using Networka:

1. **Credentials**: Always use environment variables for credentials, never hardcode them
2. **Network Access**: Ensure proper network segmentation and access controls
3. **Updates**: Keep Networka updated to the latest version
4. **Permissions**: Run with minimal required permissions
5. **Logging**: Review logs for unusual activity

## Dependencies

We regularly update dependencies to address security vulnerabilities. Use `uv sync` to ensure you have the latest secure versions.
