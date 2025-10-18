# Testing Documentation Guide

## Quick Reference

This project has three testing-related documents. Here's when to use each:

### 📘 For Project Maintainers

**File:** `MANDATORY_TESTING.md`

**Use when:**
- Making code changes to this project
- Before committing
- Need to know what tests to run

**Contains:**
- Specific tests for this project
- Word preservation test procedures
- Pass/fail criteria
- Complete test workflow
- Historical bug reference

**Quick command:**
```bash
python test_word_preservation.py input.json output.srt
```

---

### 📗 For New Project Developers

**File:** `MANDATORY_TESTING_TEMPLATE.md`

**Use when:**
- Starting a new project
- Setting up quality assurance
- Need a testing framework template

**Contains:**
- Generic template you can copy
- Example test structures
- Best practices
- CI/CD integration examples
- Troubleshooting guide

**How to use:**
1. Copy template to your new project
2. Rename to `MANDATORY_TESTING.md`
3. Fill in your specific tests
4. Customize thresholds and criteria

---

### 📕 For All Users (Quick Reference)

**File:** `claude.md` (this project's main docs)

**Use when:**
- Learning about the project
- Need quick overview of features
- Want to see recent bug fixes

**Contains:**
- Project overview
- Key features
- Usage examples
- **Brief mention** of mandatory testing with link to full docs
- Bug fix history

**Testing section says:**
> See `MANDATORY_TESTING.md` for complete testing requirements

---

## Document Relationships

```
claude.md
    ├── Brief mention of mandatory testing
    └── Links to → MANDATORY_TESTING.md
                       ├── Complete test procedures for THIS project
                       ├── Specific commands and thresholds
                       └── Historical bugs and lessons learned

MANDATORY_TESTING_TEMPLATE.md
    ├── Generic template for NEW projects
    ├── Copy and customize for your needs
    └── Independent of this project's specifics
```

---

## For This Project (subtitle-processing-experiments)

### I'm a developer working on this codebase

✅ Read: `MANDATORY_TESTING.md`
- Run tests before every commit
- Minimum: Word preservation test must pass (≥99%)
- Full suite takes 5-10 minutes

### I'm starting a similar project

✅ Read: `MANDATORY_TESTING_TEMPLATE.md`
- Copy to your project
- Customize for your needs
- Add your specific tests

### I just want to use the subtitle tools

✅ Read: `claude.md`
- Usage examples
- Feature descriptions
- No need to run tests unless modifying code

---

## Testing Philosophy

### Why separate documents?

1. **claude.md** = User-facing documentation
   - Focused on features and usage
   - Quick reference
   - Links to detailed docs

2. **MANDATORY_TESTING.md** = Developer requirements
   - Detailed test procedures
   - Project-specific
   - Complete workflows

3. **MANDATORY_TESTING_TEMPLATE.md** = Reusable template
   - Generic structure
   - Best practices
   - Can be copied to other projects

### Principle: "Right info, right place, right time"

- Users shouldn't wade through testing details to learn features
- Developers need comprehensive test procedures
- New projects benefit from proven templates

---

## Quick Start: Setting Up Testing for a New Project

```bash
# 1. Copy the template
cp MANDATORY_TESTING_TEMPLATE.md /path/to/new-project/MANDATORY_TESTING.md

# 2. Edit and customize
cd /path/to/new-project
nano MANDATORY_TESTING.md  # Fill in your specific tests

# 3. Create test scripts
touch test_data_integrity.py
# Implement your tests...

# 4. Add to git
git add MANDATORY_TESTING.md test_data_integrity.py
git commit -m "Add mandatory testing framework"

# 5. Run tests
python test_data_integrity.py input.txt output.txt

# 6. Add to CI/CD
# See template for GitHub Actions / GitLab CI examples
```

---

## Maintenance

### When to update each document:

| Document | Update When |
|----------|-------------|
| `claude.md` | Feature changes, major bugs, new capabilities |
| `MANDATORY_TESTING.md` | New tests added, thresholds changed, new bugs discovered |
| `MANDATORY_TESTING_TEMPLATE.md` | Best practices evolve, new patterns discovered |

### Review cycle:
- `claude.md` - After every feature release
- `MANDATORY_TESTING.md` - After every test change
- `MANDATORY_TESTING_TEMPLATE.md` - Quarterly or after major lessons learned

---

## FAQ

**Q: Do I need all three documents?**

A: For this project, yes. For your new project, you only need one (`MANDATORY_TESTING.md` copied from template).

**Q: Why not put everything in README.md?**

A: Separation of concerns. README is for users, MANDATORY_TESTING is for developers. Different audiences, different needs.

**Q: Can I modify the template?**

A: Yes! It's meant to be customized. Add sections, remove what you don't need, adjust thresholds.

**Q: What if my project doesn't need mandatory testing?**

A: Every project that processes or transforms data needs testing. Even simple scripts benefit from verification. The 38% data loss bug in this project proves why.

**Q: How do I know what tests to add?**

A: Start with data integrity (input count = output count). Add tests whenever you discover bugs. Think about edge cases. See the template for examples.

---

## Summary

| I want to... | Read this... |
|--------------|--------------|
| Use the subtitle tools | `claude.md` |
| Modify code in this project | `MANDATORY_TESTING.md` |
| Start a new project with tests | `MANDATORY_TESTING_TEMPLATE.md` |
| Understand the bug that was fixed | `BUG_FIX_SUMMARY.md` |
| See verification results | `VERIFICATION_REPORT.md` |
| Understand the debug session | `SESSION_SUMMARY_20251013.md` |

---

**Remember:** Good documentation is like good code - clear, concise, and serves its specific purpose.
