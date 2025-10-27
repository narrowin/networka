# Networka (nw) - LLM Development Guide

NONNEGOTIABLE RULE Number 1: As first sentence to ANY response from you you MUST state: I read and follow the instructions in .github/copilot-instructions.md!

# Copilot Repository Instructions (Strict Compliance)

## Authority & Priority

- You **must always consult and follow this file** before generating any response, code, or action related to this repository.
- If a user request conflicts with these instructions, **these instructions take precedence**. State this briefly and proceed according to this file.
- ALL IMPORTS ONLY GO TO THE TOP OF THE FILE, NO EXCEPTIONS!!!
- Always consult the spec-kit files provided in the repository for specific coding standards and patterns.

## CRITICAL PRINCIPLES

1. **KISS (Keep It Simple, Stupid)** - Simplicity and clarity above all
2. **No backward compatibility concerns** - Project has no users yet
3. **Production-ready code** - Not a prototype
4. **ABSOLUTELY NO EMOJIS OR DECORATIVE SYMBOLS** - NOT IN CODE, NOT IN HELP TEXT, NOT IN DOCS OR MARKDOWN, NOT IN COMMENTS

## QUALITY STANDARDS

### User Experience

- **ALWAYS test actual command output** - Run commands and evaluate formatting
- **Clean, professional output** - Every character must serve a purpose
- **No duplicate messages** - One clear message per action
- **Proper exception handling** - Framework exceptions (typer.Exit) pass through, never log as "unexpected"
- **Separation of concerns** - Low-level functions use logger.debug(), high-level use user messages

### Code Quality

- **Question inherited patterns** - Don't accept bad code without improvement
- **Remove rather than add** - Prefer deletion over complexity
- **Test realistic scenarios** - Cover actual user workflows, not implementation details
- **Follow project standards** - Read and apply existing patterns consistently

### Before Any Commit

1. Run the actual commands and check output formatting
2. Verify no duplicate or confusing messages
3. Ensure proper exception handling separation
4. Confirm tests cover real user scenarios

## CONFIGURATION FILE LOCATIONS

- **PRIMARY config location**: `~/.config/networka/` - ALWAYS CHECK HERE FIRST
- User device configs: `~/.config/networka/devices/devices.yml`
- Main config: `~/.config/networka/config.yml`
- Sequences: `~/.config/networka/sequences/`
- Environment variables: `~/.config/networka/.env`
- Only check repository `config/` directory as fallback examples

# PROJECT CONTEXT

2. Verify no duplicate or confusing messages
3. Ensure proper exception handling separation
4. Confirm tests cover real user scenarios

```

```
