# Mandatory Testing Procedures

## Purpose

This document defines the **mandatory tests** that must pass before any code changes are committed to this project.

**Why mandatory testing?** Silent data loss, corruption, or incorrect outputs can go undetected without proper testing. Mandatory tests ensure quality and prevent catastrophic bugs from reaching users.

---

## When to Run Tests

Run the complete test suite:
- ✅ After ANY code changes
- ✅ Before committing to version control
- ✅ After merging branches
- ✅ Before deploying to production
- ✅ When adding new features
- ✅ When refactoring existing code

**Rule:** If you change the code, you run the tests. No exceptions.

---

## Test 1: [Primary Quality Test]

**Purpose:** [What aspect of quality you're verifying - e.g., data preservation, output correctness, performance]

**Reason:** [Why this test is critical - reference any historical bugs or known issues]

**Minimum threshold:** [Define your quality bar - e.g., 99% accuracy, 100% data preserved, <1s response time]

### Running the Test

```bash
# Command to run your test
python test_[test_name].py [input_file] [output_file]

# Example:
python test_data_integrity.py input.json output.csv
```

### Example Output

```
============================================================
[TEST NAME] - ✅ PASS
============================================================
Input records:           10,000
Output records:          9,998
Records lost:            2
============================================================
Preservation rate:       99.98%
Minimum required:        99.50%
============================================================
✅ TEST PASSED
Quality meets threshold (>=99.50%)
============================================================
```

### Pass/Fail Criteria

| Result | Condition | Action |
|--------|-----------|--------|
| ✅ PASS | [Your threshold - e.g., ≥99.5%] | Continue to next test |
| ⚠️ WARNING | [Warning zone - e.g., 98-99.5%] | Review and document |
| ❌ FAIL | [Below threshold - e.g., <98%] | **DO NOT COMMIT** |
| 🔴 CRITICAL | [Severe failure - e.g., <90%] | **STOP** - Revert changes |

### Exit Codes

- `0` = PASS
- `1` = FAIL
- `2` = ERROR (test couldn't run)

---

## Test 2: [Secondary Quality Test]

**Purpose:** [Another critical aspect to test]

**Reason:** [Why this matters]

**Minimum threshold:** [Define threshold]

### Running the Test

```bash
python test_[another_test].py [args]
```

### Pass/Fail Criteria

[Define criteria similar to Test 1]

---

## Test 3: [Additional Test if needed]

[Follow same structure]

---

## Complete Test Workflow

### Quick Test (5 minutes)

Run core tests only:

```bash
# Test 1
python test_[primary].py input.txt output.txt

# Test 2
python test_[secondary].py input.txt output.txt
```

### Full Test Suite (10-30 minutes)

Run all tests including stress tests:

```bash
./run_all_tests.sh
```

Or manually:

```bash
# Core tests
python test_[primary].py input.txt output.txt
python test_[secondary].py input.txt output.txt

# Stress tests
python test_[stress].py large_input.txt
python test_[edge_cases].py

# Performance tests
python test_[performance].py benchmark_data.txt
```

---

## Test Data

### Required Test Files

Store test data in `test_data/` directory:

```
test_data/
├── small_sample.txt          # Quick smoke test (< 1 min)
├── medium_sample.txt         # Standard test (2-5 min)
├── large_sample.txt          # Stress test (10-30 min)
├── edge_cases/               # Edge cases and known issues
│   ├── empty_input.txt
│   ├── malformed_data.txt
│   └── extreme_values.txt
└── expected_outputs/         # Known good outputs for comparison
    ├── small_expected.txt
    └── medium_expected.txt
```

### Recommended Test Data Size

- **Small:** [e.g., 100 records, runs in <1 min]
- **Medium:** [e.g., 10,000 records, runs in 2-5 min]
- **Large:** [e.g., 100,000+ records, runs in 10-30 min]

Use small for rapid iteration, medium for pre-commit, large for pre-deployment.

---

## Investigation Tools

When tests fail, use these tools to investigate:

### Tool 1: [Diagnostic Script]

```bash
python analyze_[failure_type].py [failed_output]
```

**Purpose:** [What it helps you understand]

### Tool 2: [Another Diagnostic]

```bash
python debug_[specific_issue].py [args]
```

**Purpose:** [What it reveals]

---

## Pre-Commit Checklist

Before committing code changes:

- [ ] All core tests pass (≥ threshold)
- [ ] Any failing tests documented in commit message
- [ ] New features have corresponding tests
- [ ] Breaking changes documented
- [ ] `CHANGELOG.md` updated if applicable
- [ ] `README.md` updated if behavior changed

**Minimum required:** Core tests must pass. Do not commit if tests fail.

---

## Historical Bug Reference

### [Bug Name/ID] - [Date]

**Issue:** [Brief description of the bug]

**Impact:** [What went wrong - e.g., data loss, incorrect outputs]

**Root cause:** [Technical explanation]

**Test added:** [Which test now catches this issue]

**Lesson learned:** [What this taught us]

---

### Example: Silent Data Truncation (2025-10-13)

**Issue:** Text wrapping function silently truncated content

**Impact:** 38.1% data loss (7,142 words deleted)

**Root cause:** `wrap_text()` truncated without raising error; `split_oversized_segment()` didn't detect truncation

**Test added:** Word Preservation Test (Test 1)

**Lesson learned:** Always verify output size matches input size for data processing operations

---

## Continuous Integration (CI/CD)

### GitHub Actions Example

```yaml
name: Mandatory Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run mandatory tests
        run: |
          python test_[primary].py test_data/sample.txt output.txt
          python test_[secondary].py test_data/sample.txt output.txt
```

### GitLab CI Example

```yaml
test:
  script:
    - pip install -r requirements.txt
    - python test_[primary].py test_data/sample.txt output.txt
    - python test_[secondary].py test_data/sample.txt output.txt
  only:
    - merge_requests
    - main
```

---

## Troubleshooting

### Test fails but code seems correct?

1. Check test data hasn't been corrupted
2. Verify test thresholds are appropriate
3. Review recent changes to test scripts themselves
4. Check for environment-specific issues (OS, Python version)

### Test takes too long?

1. Use smaller test data for rapid iteration
2. Run full tests only before commits
3. Consider parallel test execution
4. Profile slow tests and optimize

### How to handle legitimate test failures?

1. **Document:** Explain why the change affects the test
2. **Update threshold:** If new behavior is correct, update expected values
3. **Add new test:** If behavior changed, add test for new behavior
4. **Never:** Disable or remove tests to make them "pass"

---

## Contact

For questions about testing procedures:
- [Your contact info or team channel]
- See `README.md` for general project information
- See `CONTRIBUTING.md` for development guidelines

---

## Template Version

**Version:** 1.0
**Last updated:** [Date]
**Based on:** subtitle-processing-experiments project (2025-10-13 bug fix)

---

## Notes

- Customize this template for your specific project needs
- Add more tests as you discover new failure modes
- Update thresholds based on your quality requirements
- Keep this document in sync with actual test scripts
- Review and update periodically (e.g., quarterly)

**Remember:** Tests are only useful if they're run consistently. Make testing part of your workflow, not an afterthought.
