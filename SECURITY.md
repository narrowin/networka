# Security Policy

## Supported Versions

We provide security updates for:

- Latest stable release (current minor version)
- Previous minor version (for 90 days after new release)

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Email: info@narrowin.ch

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

## Response Timeline

- **Initial response**: Within 2 business days
- **Status update**: Within 7 days
- **Fix timeline**: Critical issues within 30 days

## Disclosure Policy

- Coordinated disclosure after fix is released
- Credit given to reporter (unless anonymity requested)

## Security Best Practices

When using Networka:

1. **Credentials**: Always use environment variables for credentials, never hardcode them
2. **Network Access**: Ensure proper network segmentation and access controls
3. **Updates**: Keep Networka updated to the latest version
4. **Permissions**: Run with minimal required permissions
5. **Logging**: Review logs for unusual activity

## Dependencies

We regularly update dependencies to address security vulnerabilities. Use `uv sync` to ensure you have the latest secure versions.
