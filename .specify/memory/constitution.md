<!--
Sync Impact Report
==================
Version Change: N/A (initial constitution) → 1.0.0
Modified Principles: N/A (initial version)
Added Sections: All sections are new
Removed Sections: N/A
Templates Requiring Updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section aligned
  ✅ .specify/templates/spec-template.md - Requirements structure aligned
  ✅ .specify/templates/tasks-template.md - Task categorization aligned
  ✅ .github/copilot-instructions.md - Development guidelines aligned
Follow-up TODOs: None
-->

# Networka Constitution

## Core Principles

### I. Code Quality and Type Safety (NON-NEGOTIABLE)

All code MUST maintain strict type safety and quality standards:

- Full type annotations required for all functions, methods, and class attributes
- MyPy type checking MUST pass with no errors in strict mode
- Ruff linting and formatting MUST be applied to all code
- PEP 8 style compliance is mandatory
- Modular architecture with clear separation between vendor-agnostic interfaces and vendor-specific implementations
- No emojis anywhere in the code or docs unless asked for!

**Rationale**: Type safety catches bugs at development time rather than runtime. Consistent formatting and linting ensure maintainability as the codebase grows. The vendor-agnostic architecture allows seamless addition of new network device platforms without disrupting existing functionality.

### II. Functional Testing First (NON-NEGOTIABLE)

Testing focuses on functional validation of user-facing features:

- Functional tests MUST be written for all main CLI commands and workflows
- Tests MUST validate actual user scenarios, not implementation details
- All network operations MUST be properly mocked in tests
- Unit tests will be added incrementally for critical components
- Integration tests MUST cover multi-device operations and concurrent scenarios

**Rationale**: Functional tests ensure that the tool works correctly from the user's perspective. This approach prioritizes delivering working features over achieving theoretical coverage metrics. Mocking network operations ensures tests are fast, reliable, and don't require actual hardware.

### III. Security by Design

Security MUST be integrated throughout the development lifecycle:

- Static analysis and vulnerability scanning MUST be part of CI pipeline
- Secret detection MUST run on all commits to prevent credential leaks
- Credentials MUST NEVER be stored in configuration files
- All credential handling MUST use environment variables or interactive prompts
- Security audit (pip-audit) MUST pass before any release
- Dependency updates MUST be reviewed for security implications

**Rationale**: Network automation tools handle sensitive credentials and access critical infrastructure. Security cannot be an afterthought. Environment variables and prompts prevent accidental credential exposure in version control or configuration files.

### IV. User Experience Consistency

The CLI MUST provide a consistent, intuitive interface:

- Commands MUST have sensible defaults that work for common cases
- Error messages MUST be helpful and actionable, guiding users to solutions
- Output MUST be rich but non-intrusive, with clear status indicators
- Configuration MUST use YAML/CSV with well-documented schemas
- All cli-features MUST include shell completion support
- Help text and documentation MUST be clear, professional, and free of decorative symbols

**Rationale**: Network engineers need tools that are efficient and predictable. Good UX reduces errors, speeds up workflows, and lowers the learning curve. Backward compatibility ensures existing automation scripts continue to work.

### V. Performance and Scalability

The toolkit MUST scale efficiently across many devices:

- Concurrent operations (commands, backups, uploads) MUST not block
- File transfers MUST handle large files efficiently without loading entire content into memory
- Connection pooling and reuse MUST be employed where supported by transport
- Resource consumption (memory, CPU, file descriptors) MUST scale linearly or better with device count
- Timeout handling MUST account for device resource limitations and slow networks
- Batch operations MUST provide progress indicators for long-running tasks
- Performance degradation MUST be profiled and addressed when operating at scale (100+ devices)

**Rationale**: Network automation often involves hundreds or thousands of devices. Sequential operations are too slow and don't scale. Async operations allow managing many devices concurrently without excessive resource consumption. Memory-efficient file handling prevents crashes with large firmware images. Proper timeout and progress handling improves user experience during long operations.

### VI. Vendor-Agnostic Architecture

Multi-vendor support MUST follow consistent patterns:

- Core interfaces MUST be vendor-agnostic
- Vendor-specific implementations MUST be isolated in dedicated modules
- New vendor support MUST not require changes to core logic
- All vendors MUST support the same basic operations (commands, backups, file transfers)
- Vendor differences MUST be abstracted through common interfaces
- Documentation MUST clearly indicate vendor-specific features

**Rationale**: Network environments are heterogeneous. A vendor-agnostic design allows the tool to work across diverse infrastructure without forcing users to learn different tools for different platforms.

### VII. Documentation Completeness

Documentation MUST be comprehensive and current:

- All features MUST be documented before merging
- Installation, configuration, and usage MUST have clear guides
- Environment variables MUST be documented with examples
- Command reference MUST be auto-generated and complete
- Multi-vendor capabilities MUST be clearly documented per platform
- Advanced features MUST include working examples
- Documentation updates MUST accompany all functional changes

**Rationale**: Undocumented features are invisible to users. Complete documentation reduces support burden and enables users to self-serve. Auto-generated reference docs ensure accuracy.

## Technical Standards

### Language and Environment

- **Python Version**: 3.11, 3.12, or 3.13 required
- **Platform Support**: Linux, macOS, Windows (with WSL for Windows)
- **Package Manager**: uv for dependency management and task execution
- **CLI Framework**: Typer with Rich for output formatting
- **Network Library**: Scrapli for device communication
- **Validation**: Pydantic v2 for configuration and data validation

### Code Organization

All code MUST follow these structural patterns:

```text
src/network_toolkit/
├── cli.py              # Typer CLI entry points
├── device.py           # Device session management
├── config.py           # Pydantic configuration models
├── exceptions.py       # Custom exception hierarchy
├── results.py          # Results handling and storage
└── vendors/            # Vendor-specific implementations
    ├── mikrotik/
    ├── cisco/
    └── ...

tests/
├── conftest.py         # Shared fixtures and mocks
├── functional/         # User scenario tests
└── unit/               # Component tests (as needed)
```

### Exception Handling

All custom exceptions MUST derive from the project exception hierarchy:

```text
NetworkToolkitError (base)
├── ConfigurationError
├── DeviceConnectionError
├── DeviceExecutionError
├── FileTransferError
├── DeviceAuthError
└── DeviceTimeoutError
```

Framework exceptions (typer.Exit) MUST pass through without additional logging.

### Quality Gates

All code MUST pass these checks before merge:

- **Ruff Check**: `ruff check src/ tests/ --fix` (via VS Code task)
- **Ruff Format**: `ruff format src/ tests/` (via VS Code task)
- **MyPy**: `mypy src/network_toolkit` (via VS Code task)
- **Functional Tests**: All functional tests MUST pass (via VS Code test feature)
- **Security Audit**: `pip-audit` MUST show no critical vulnerabilities

## Development Workflow

### Code Changes

All code changes MUST follow this process:

1. Create feature branch with descriptive name
2. Implement changes with functional tests
3. Run quality checks via VS Code tasks
4. Verify tests pass via VS Code test feature
5. Update documentation as needed
6. Submit pull request with clear description

### Testing Requirements

All new features MUST include:

- Functional tests covering main user scenarios
- Proper mocking of all external dependencies (network, filesystem, subprocess)
- Test documentation explaining what is being validated
- Edge case coverage for error conditions

### Code Review Standards

All pull requests MUST:

- Pass all automated quality gates
- Include functional tests for new features
- Update documentation for user-facing changes
- Document breaking changes
- Follow the KISS principle (prefer simplicity)

## Security Standards

### Credential Management

- Default credentials via `NW_USER_DEFAULT` and `NW_PASSWORD_DEFAULT`
- Device-specific overrides via `NW_{DEVICE}_USER` and `NW_{DEVICE}_PASSWORD`
- Interactive prompts for missing credentials
- NEVER hardcode credentials in any form

### CI/CD Security

- CodeQL security scanning on all commits
- Dependency vulnerability scanning (pip-audit)
- Secret detection to prevent credential leaks
- Security audit MUST pass before release

## Open Source Governance

### Licensing

- Project licensed under Apache-2.0
- All contributions MUST comply with Apache-2.0 terms
- Mixed MIT/SPDX headers in existing code will be standardized
- Contributors MUST not introduce incompatible licenses

### Community Engagement

- Issue responses MUST be timely and helpful
- Pull requests MUST receive feedback within reasonable timeframes
- Feature requests MUST be evaluated against core mission
- New vendor support MUST align with vendor-agnostic architecture
- Breaking changes MUST be clearly communicated

## Governance

This constitution supersedes all other development practices and guidelines. All code reviews, pull requests, and architectural decisions MUST verify compliance with these principles.

**Amendment Process**:

- Amendments require documentation of rationale and impact
- Version MUST increment according to semantic versioning
- Templates and dependent documentation MUST be updated
- Migration plan required for breaking governance changes

**Version Semantics**:

- MAJOR: Backward incompatible governance/principle removals or redefinitions
- MINOR: New principle/section added or materially expanded guidance
- PATCH: Clarifications, wording improvements, non-semantic refinements

**Compliance**:

- All PRs MUST be checked against constitution requirements
- Violations MUST be justified with clear rationale
- Runtime development guidance provided in `.github/copilot-instructions.md`

**Version**: 1.0.0 | **Ratified**: 2025-10-16 | **Last Amended**: 2025-10-16
