# Security Quick Reference Guide

**For:** `json_to_srt_energy.py`
**Status:** Production Ready ✅
**Last Updated:** 2025-10-17

---

## Security Limits

| Resource | Limit | Configurable |
|----------|-------|--------------|
| Audio file size | 500MB | Yes (line 61) |
| JSON file size | 100MB | Yes (line 62) |
| Max segments | 10,000 | Yes (line 63) |
| Max words/segment | 1,000 | Yes (line 64) |
| Allowed audio formats | .mp3, .wav, .flac, .ogg, .m4a, .aac, .wma | Yes (line 60) |

---

## Security Functions

### Path Validation
```python
validate_file_path(file_path, base_dir=None, must_exist=False)
```
- **Location:** Lines 78-118
- **Protects:** Path traversal, symlink attacks
- **Returns:** Validated Path object
- **Raises:** ValueError, FileNotFoundError

### Audio Validation
```python
validate_audio_file(audio_path, base_dir=None)
```
- **Location:** Lines 121-161
- **Protects:** Invalid formats, oversized files, path traversal
- **Returns:** Validated Path object
- **Raises:** ValueError, FileNotFoundError

### JSON Loading
```python
safe_json_load(file_path)
```
- **Location:** Lines 164-239
- **Protects:** Oversized files, malformed JSON, DoS attacks
- **Returns:** Parsed JSON dict
- **Raises:** ValueError

### Safe Writing
```python
safe_write_file(output_path, content)
```
- **Location:** Lines 242-294
- **Protects:** Race conditions, partial writes, path traversal
- **Returns:** None
- **Raises:** ValueError, PermissionError, RuntimeError

---

## Testing

### Run All Security Tests
```bash
# Automated test suite (30 tests)
python -m pytest test_security.py -v

# Attack scenarios (10 tests)
python test_attack_scenarios.py

# Both should show 100% pass rate
```

### Expected Results
```
✅ 30 automated tests passed
✅ 10 attack scenarios blocked
✅ All security functions validated
```

---

## Monitoring

### Security Log Location
```
./json_to_srt_energy.log
```

### Important Events to Monitor

**WARNING Level:**
- Path traversal attempts
- File size violations
- Invalid file formats
- Structure validation failures

**ERROR Level:**
- JSON parsing errors
- Permission denied
- File write failures

### Example Log Entries
```
2025-10-17 11:48:02,099 - json_to_srt_energy - WARNING - Path outside base directory: ../../etc/passwd
2025-10-17 11:48:02,103 - json_to_srt_energy - WARNING - Audio file too large: 500.0MB
2025-10-17 11:48:02,117 - json_to_srt_energy - ERROR - Invalid JSON format
```

---

## Common Security Errors

### Path Traversal Detected
```
Error: Invalid input - Path ../../file is outside allowed directory
```
**Cause:** Attempting to access files outside working directory
**Action:** Use absolute paths or paths relative to current directory

### File Too Large
```
Error: Invalid input - Audio file too large: 600.0MB (maximum 500MB)
```
**Cause:** File exceeds size limit
**Action:** Reduce file size or increase limit (line 61)

### Invalid Format
```
Error: Invalid input - Unsupported audio format: .xyz
```
**Cause:** File extension not in whitelist
**Action:** Convert to supported format or add extension to whitelist (line 60)

### Too Many Segments
```
Error: Invalid input - Too many segments in JSON: 15000 (maximum 10000)
```
**Cause:** JSON exceeds segment limit
**Action:** Split into multiple files or increase limit (line 63)

---

## Emergency Response

### If Security Breach Suspected

1. **Check logs immediately:**
   ```bash
   tail -100 json_to_srt_energy.log | grep -i "warning\|error"
   ```

2. **Look for patterns:**
   - Multiple path traversal attempts
   - Repeated authentication failures
   - Large file upload attempts

3. **Review recent file access:**
   ```bash
   ls -lat | head -20
   ```

4. **Check for unauthorized files:**
   ```bash
   find . -type f -mtime -1
   ```

---

## Configuration Changes

### Increase File Size Limits

**File:** `json_to_srt_energy.py`

```python
# Line 61 - Audio file limit
MAX_AUDIO_FILE_SIZE = 1000 * 1024 * 1024  # 1GB

# Line 62 - JSON file limit
MAX_JSON_FILE_SIZE = 200 * 1024 * 1024   # 200MB
```

**Restart:** Not required (applies on next execution)

### Add Audio Format

**File:** `json_to_srt_energy.py`

```python
# Line 60 - Add .opus
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.opus'}
```

### Increase Segment Limits

**File:** `json_to_srt_energy.py`

```python
# Line 63 - Max segments
MAX_SEGMENTS = 20000  # Increased from 10000

# Line 64 - Max words per segment
MAX_WORDS_PER_SEGMENT = 2000  # Increased from 1000
```

---

## Best Practices

### For Users

1. ✅ **Use relative paths** within project directory
2. ✅ **Keep files under size limits** (split if needed)
3. ✅ **Use supported audio formats** (.mp3, .wav, .flac, etc.)
4. ✅ **Validate JSON structure** before processing
5. ✅ **Check logs** after processing

### For Administrators

1. ✅ **Review logs weekly** for suspicious activity
2. ✅ **Monitor disk usage** for large files
3. ✅ **Update limits** based on legitimate usage patterns
4. ✅ **Archive logs monthly**
5. ✅ **Run security tests** after code changes

### For Developers

1. ✅ **Never bypass security functions** directly
2. ✅ **Always use validated paths** from security functions
3. ✅ **Test security** after changes (run `test_security.py`)
4. ✅ **Log security events** at appropriate levels
5. ✅ **Document security implications** of changes

---

## Troubleshooting

### Tests Fail After Code Changes

```bash
# Run security tests
python -m pytest test_security.py -v

# If failures, check:
# 1. Did you modify security functions?
# 2. Did you change constants?
# 3. Are paths being validated?
```

### Legitimate Files Rejected

**Problem:** Valid files trigger security errors

**Solutions:**
1. Check file size against limits
2. Verify file extension is in whitelist
3. Ensure path doesn't contain ".."
4. Check JSON structure matches schema

### Performance Issues

**Problem:** Processing slower after security fixes

**Analysis:**
- Security overhead: <0.5% typically
- If significantly slower, check:
  - File system performance
  - Log file size (rotate if large)
  - Network drives (use local storage)

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| `SECURITY_AUDIT_REPORT.md` | Complete vulnerability analysis |
| `SECURITY_FIXES_SUMMARY.md` | Detailed implementation guide |
| `SECURITY_IMPLEMENTATION_COMPLETE.md` | Final verification results |
| `SECURITY_QUICK_REFERENCE.md` | This document - quick reference |
| `test_security.py` | Automated test suite |
| `test_attack_scenarios.py` | Attack simulation tests |

---

## Quick Commands

```bash
# Run all security tests
python -m pytest test_security.py -v && python test_attack_scenarios.py

# Check recent security events
tail -50 json_to_srt_energy.log | grep WARNING

# Count security violations today
grep "$(date +%Y-%m-%d)" json_to_srt_energy.log | grep -c WARNING

# Process file with security checks
python json_to_srt_energy.py audio.mp3 transcript.json

# View log in real-time
tail -f json_to_srt_energy.log
```

---

## Contact

**For security issues:**
- Review logs: `json_to_srt_energy.log`
- Run diagnostics: `test_security.py`
- Check documentation: `SECURITY_AUDIT_REPORT.md`

**For configuration help:**
- See: Lines 60-64 in `json_to_srt_energy.py`
- Test changes: Run security test suite

---

**Last Updated:** 2025-10-17
**Status:** ✅ Secure and Production Ready
