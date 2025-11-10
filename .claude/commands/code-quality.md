# Code Quality Verification Command

Performs comprehensive code quality analysis and systematic fixes using the specialized code quality agent.

## Usage

This command delegates to the `code-quality-specialist` agent that knows all project-specific standards and patterns.

### With specific file(s)

```txt
@code-quality path/to/file.py
@code-quality src/module.py tests/test_module.py
```

### For entire project

```txt
@code-quality
```

## What it does

The code quality specialist will:

1. **Analyze** - Run ruff, mypy, and other quality checks
2. **Diagnose** - Identify root causes and systemic issues
3. **Fix** - Apply systematic fixes following project standards
4. **Verify** - Ensure zero errors and architectural compliance
5. **Report** - Provide detailed analysis and recommendations

## Agent Expertise

The specialist agent has deep knowledge of:

- Python 3.12+ type system and modern patterns
- Project architecture (domain-driven design)
- Testing conventions and pytest best practices
- API implementation rules and error handling
- Service naming and Docker configuration
- Frontend TypeScript standards

---

$ARGUMENTS

I'll delegate this to our code quality specialist agent who has comprehensive knowledge of our project standards and will perform thorough analysis and fixes.
