# CRC Mismatch Issue & Workaround

## Problem Summary

The **real UG405 controller** at IP `10.164.95.208` sends XKOP packets with CRC values that don't match any known CRC16 algorithm:

```
Packet: CA 35 02 00 00 00 00 00 00 00 00 00 00 00 00 9B A0
        └─────────────── data (15 bytes) ──────────────┘ └crc┘

Expected CRC: 9B A0
Calculated:   53 69  ❌ MISMATCH!
```

## Investigation Results

We tested **extensive CRC variations**:

✗ 11 standard CRC16 algorithms (CCITT, XMODEM, MODBUS, etc.)
✗ Official XKOP table-based algorithm
✗ 32 variations of init values (0x00, 0xFF, combinations)
✗ 32 variations of XOR final values
✗ 16 different byte ordering combinations
✗ 8 alternative lookup strategies

**NONE matched the real controller's CRC values.**

## Analysis

The real controller uses a **custom/proprietary CRC algorithm** that is:

1. Not documented in available specifications
2. Not matching any standard CRC16 variant
3. Not matching the "official" algorithm used by the simulator
4. Blocking all communication with the real hardware

## Workaround Solution

Since communication is blocked and the correct CRC is unknown, we've implemented a **configurable CRC bypass**:

### Configuration

In `app.py` line ~89:

```python
DISABLE_CRC_VALIDATION = True  # Set to False to enable strict CRC validation
```

### Modes

**DISABLE_CRC_VALIDATION = True (default)**
- ✓ Works with real UG405 controller
- ✓ Accepts all packets regardless of CRC
- ⚠️  No error detection - corrupted packets will be processed
- ⚠️  Use ONLY with trusted/direct connections

**DISABLE_CRC_VALIDATION = False**
- ✓ Strict CRC validation (error detection enabled)
- ✓ Works with simulator (`windows_xkop_controller.py`)
- ✗ Rejects all packets from real controller

### Indicators

When CRC validation is disabled, you'll see:

**At startup:**
```
============================================================
XKOP Tool - CLIENT MODE
============================================================
⚠️  WARNING: CRC VALIDATION IS DISABLED
   Error detection is OFF - use only with real UG405 controller
============================================================
```

**On first packet:**
```
[06:10:40]   ⚠️  CRC VALIDATION DISABLED - error detection is OFF!
[06:10:40] RX from ('10.164.95.208', 8001): [(0, 1), (1, 0), (3, 1)]
```

## Recommendations

### Short Term (Current Solution)

✓ Use `DISABLE_CRC_VALIDATION = True` to work with real controller
✓ Ensure direct/trusted connection (LAN, no internet exposure)
✓ Monitor logs for communication errors
✓ Consider using TCP (more reliable than UDP)

### Medium Term

Try to reverse engineer the CRC:

1. **Capture 20+ packets** from the real controller with known data
2. **Use CRC RevEng tool:**
   ```bash
   reveng -w 16 -s CA3502000000000000000000000000 9BA0
   ```
3. **Analyze patterns** in the CRC values vs data

### Long Term (Best Solution)

1. **Contact UG405 manufacturer/vendor**
   - Request official XKOP protocol specification
   - Ask for CRC algorithm details
   - Get firmware version info

2. **Firmware investigation**
   - Check controller firmware version
   - See if firmware update available
   - Test if newer firmware matches standard algorithm

3. **Alternative protocol**
   - Check if controller supports other protocols
   - Consider using manufacturer's official software/SDK

## Testing

### Test with Simulator (CRC enabled)

```bash
# Terminal 1: Start simulator
python3 windows_xkop_controller.py

# Terminal 2: Set DISABLE_CRC_VALIDATION = False in app.py, then:
python3 app.py
```

Should see: `✓ Valid CRC` messages

### Test with Real Controller (CRC disabled)

```bash
# Set DISABLE_CRC_VALIDATION = True in app.py
python3 app.py
```

Should see: Packets accepted despite CRC mismatch

## Technical Details

### Packets Analyzed

| Data (15 bytes) | Expected CRC | Calculated CRC | Algorithms Tested |
|----------------|--------------|----------------|-------------------|
| CA 35 02 00... | 9B A0 | 53 69 | 50+ variations |
| CA 35 00 00 00 01 01... | 99 7C | 51 B5 | 50+ variations |
| CA 35 00 03 00 01 FF... | D6 90 | 1E 59 | 50+ variations |
| CA 35 00 01 00 01 FF... | AF 4D | 67 84 | 50+ variations |
| CA 35 00 00 00 00 01... | 6F 31 | A7 F8 | 50+ variations |

None of the 50+ tested algorithm variations matched ANY packet.

### CRC Table Used

The implementation uses a 256-entry CRC16 table:

```python
CRC_TABLE = [
    0x0000, 0x0f89, 0x1f12, 0x109b, 0x3e24, 0x31ad, 0x2136, 0x2ebf,
    # ... (full table in app.py)
]
```

This table appears to be for a standard CRC-16/CCITT variant, but the algorithm that uses it differs from the controller's.

## Security Considerations

**Disabling CRC validation removes error detection:**

- Corrupted packets will be processed as valid
- Bit flips during transmission won't be detected
- Malformed data could cause unexpected behavior

**Mitigation:**

- Use on trusted LANs only
- Don't expose to internet
- Use TCP instead of UDP (TCP has its own checksums)
- Monitor logs for anomalies
- Consider additional validation at application level

## Files Modified

- `app.py` line ~89: Added `DISABLE_CRC_VALIDATION` flag
- `app.py` line ~260: Modified CRC validation logic
- `app.py` line ~944: Added startup warning message

## Related Files

- `test_real_controller_crc.py` - Tests with real controller packets
- `test_table_based_variations.py` - Tests algorithm variations
- `test_alternative_lookup.py` - Tests alternative lookup strategies
- `CRC_FIX_SUMMARY.md` - Previous CRC fix attempt
- `FINDINGS_SUMMARY.md` - Detailed CRC analysis

## Questions?

If you:
- Have access to official protocol documentation
- Can contact the controller manufacturer
- Have captured more packet samples
- Have access to controller firmware

Please share! This would help implement the correct CRC algorithm.

## Status

✓ **Workaround implemented** - System can communicate with real controller
⚠️  **Error detection disabled** - Monitor for issues
❓ **Root cause unknown** - Custom CRC algorithm needs manufacturer documentation

---

**Last Updated:** 2025-11-09
**Branch:** claude/fix-crc-mismatch-errors-011CUwpcwHQExvtFCo5CXt8U
