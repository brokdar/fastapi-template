---
name: test-analyzer
description: Comprehensive test failure analysis and resolution. Use when the user provides test commands to execute (e.g., pytest, npm test) or test output/results from previous runs. Performs deep analysis, identifies root causes, clusters related failures, and implements optimal fixes following best practices. Suitable for any test framework (pytest, jest, mocha, junit, etc.)
---

# Test Failure Analysis and Resolution

Expert analysis of test failures with root cause identification and optimal solution implementation.

## Input Handling

Parse the user's input to determine the mode:

1. **Execute mode**: User provides test commands (e.g., `pytest tests/`, `npm test`)
2. **Analysis mode**: User provides test output or failure logs

## Workflow

### 1. Test Execution/Collection

**Execute mode:**

- Run the provided test command
- Capture complete output including errors, stack traces, and summary

**Analysis mode:**

- Parse provided output
- Extract all failure information

### 2. Deep Failure Analysis

For each failed test, extract:

- Test identifier and location (file, line number)
- Error type (AssertionError, TypeError, AttributeError, timeout, etc.)
- Complete error message and stack trace
- Test type (unit, integration, e2e)

Perform root cause analysis by:

- Examining test code and code under test
- Identifying logic errors, type mismatches, incorrect assertions
- Checking for timing issues, race conditions, flaky behavior
- Analyzing dependencies and side effects
- Verifying test assumptions and setup/teardown

### 3. Error Clustering

Group failures by shared characteristics:

**By error type:**

- Same exception class
- Similar error messages
- Common patterns (e.g., all KeyError, all timeout)

**By location:**

- Same module/component
- Related functionality
- Shared dependencies

**By pattern:**

- Timing-related (intermittent, race conditions)
- Data-related (missing fixtures, wrong test data)
- Configuration (environment variables, paths)
- Setup/teardown issues

### 4. Solution Development

For each cluster, determine the optimal fix:

**Prioritize root causes over symptoms:**

- Fix the underlying issue, not just the failing assertion
- Avoid workarounds and hacks
- Consider long-term maintainability

**Solution categories:**

- **Code bugs**: Logic errors, type issues, incorrect implementations
- **Test issues**: Wrong assertions, outdated tests, poor isolation
- **Configuration**: Missing setup, wrong environment, incorrect test data
- **Design problems**: Architecture requiring refactoring

**Priority order:**

1. Critical failures blocking other tests
2. Fixes resolving multiple failures
3. Simple bugs with clear solutions
4. Complex refactoring

### 5. Implementation

Apply fixes systematically:

1. Implement in priority order
2. Maintain code style and add type hints where applicable
3. Re-run tests after each fix to verify
4. Ensure no regression in passing tests

## Output Format

Provide a structured report:

### Executive Summary

```
Total tests: X
Failed: Y
Unique issues: Z
Success rate after fixes: N%
```

### Failure Analysis

For each cluster:

**Issue**: Clear problem description

**Root Cause**: Technical explanation

**Affected Tests**:

- `test_function_name` (file.py:123)
- ...

**Solution**: What needs to be fixed and why

**Implementation**: Specific code changes

### Implementation Log

```
Modified: src/module.py
- Fixed type error in function_name()
- Updated assertion in test_function()

Fixed tests:
✓ test_case_1
✓ test_case_2

Remaining: 0
```

### Recommendations

- Patterns to avoid in future
- Test improvements (better isolation, clearer assertions)
- Potential refactoring opportunities

## Best Practices

**Code quality:**

- Follow existing style
- Add type hints (Python 3.12+)
- Clear, self-documenting code
- Proper error handling

**Testing principles:**

- Deterministic tests (no random failures)
- Isolated tests (no interdependencies)
- Proper setup/teardown
- Mock external dependencies
- Descriptive test names

**Common fixes:**

- **Type errors**: Add proper type hints, fix type mismatches
- **Assertion errors**: Verify expected vs actual, update assertions
- **Import errors**: Fix module paths, add missing dependencies
- **Timeout errors**: Optimize slow code, increase timeouts if justified
- **Flaky tests**: Identify and remove non-determinism

## Error Handling

If unable to fix certain issues:

1. Clearly document the blocker
2. Suggest investigation paths
3. Provide partial solutions
4. Mark tests as skipped with clear reasons using `pytest.mark.skip` or equivalent

Begin analysis immediately when test information is provided.
