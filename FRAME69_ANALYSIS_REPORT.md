# Frame 69 TCP Packet Analysis Report

## Executive Summary

The TCP packet from Frame 69 contains an **INVALID CRC** according to the current XKOP parser implementation. The real UG405 controller is generating packets with CRCs that don't match the expected algorithm.

## Packet Details

### Frame 69 TCP Payload
```
Raw hex: CA3500000000010001020001FF00009847
Length: 17 bytes
```

**Header:**
- HDR1: 0xCA ✓
- HDR2: 0x35 ✓
- Type: 0x00 (DATA message)

**Records:**
- Record 1: Index   0 = 0
- Record 2: Index   1 = 1
- Record 3: Index   2 = 1
- Record 4: Empty (0xFF)

**CRC Analysis:**
- Received CRC bytes: `98 47`
- As little-endian: 0x4798
- As big-endian: 0x9847

### Current Parser Calculation
- Expected CRC (calculated): 0x8E50
- Packed as little-endian: `50 8E`
- **MISMATCH**: Calculated 0x8E50 != Received 0x4798

### Windows Controller Calculation
- Expected CRC (bytes): `50 8E`
- **MISMATCH**: Calculated `50 8E` != Received `98 47`

## Error Log Packet (Different Packet!)

The error message shows a **DIFFERENT** packet:
```
Raw hex: CA35020000000000000000000000009BA0
Type: 0x02 (STATUS)
CRC: 9B A0
Expected CRC: 53 69
```

This is NOT Frame 69! This suggests multiple packets are failing CRC validation.

## Root Cause Analysis

### 1. CRC Algorithm Mismatch

The real UG405 controller is using a **DIFFERENT** CRC16 algorithm than implemented in the parser. Evidence:

| Data | Expected CRC (parser) | Actual CRC (controller) | Match? |
|------|----------------------|------------------------|--------|
| Frame 69 data | 0x508E | 0x9847 | ✗ NO |
| Error log data | 0x5369 | 0x9BA0 | ✗ NO |

### 2. Possible Causes

1. **Different CRC polynomial** - The controller may use a different CRC16 polynomial
2. **Different initial value** - CRC may start with non-zero seed
3. **Different bit/byte ordering** - Reflected vs non-reflected CRC
4. **Different final XOR** - Some CRC16 variants XOR the result

### 3. Common CRC16 Variants

The current implementation appears to be CRC16-CCITT-FALSE, but the controller might be using:
- CRC16-MODBUS
- CRC16-IBM
- CRC16-XMODEM
- CRC16-ARC
- Or a custom variant

## Impact

**All packets from the real controller are being REJECTED** due to CRC validation failure. This prevents:
- Reading output values from the controller
- Responding to controller requests
- Normal XKOP protocol operation

## Recommendations

### Option 1: Reverse Engineer the Correct CRC (Recommended)

Capture multiple valid packets from the real controller and use CRC RevEng tool to determine the exact CRC algorithm:

```bash
# Install reveng
sudo apt-get install reveng

# Analyze packets
reveng -w 16 -s <data1> <crc1> <data2> <crc2> ...
```

### Option 2: Temporarily Disable CRC Validation

For testing purposes only, modify `app.py` to skip CRC checks:

```python
# In parse_xkop_packet() around line 224
# Comment out CRC validation:
# if calc != recv:
#     log_xkop(f"  Parse fail: CRC mismatch...")
#     return None
```

**WARNING**: This removes error detection and should only be used temporarily!

### Option 3: Contact Controller Manufacturer

Request the official CRC16 specification from the UG405 controller manufacturer.

## Next Steps

1. ✓ Analyzed Frame 69 packet structure
2. ✓ Identified CRC mismatch
3. ✓ Confirmed algorithm incompatibility
4. ⏳ Determine correct CRC algorithm
5. ⏳ Update parser to use correct CRC
6. ⏳ Validate with real controller packets

## Test Data for CRC Analysis

For use with CRC reverse engineering tools:

```
Data 1 (15 bytes): CA3500000000010001020001FF0000
CRC 1: 9847

Data 2 (15 bytes): CA3502000000000000000000000000
CRC 2: 9BA0
```

## Files Modified

- None yet - awaiting CRC algorithm identification

## Additional Notes

- The `windows_xkop_controller.py` simulator uses the same CRC algorithm as `app.py`
- Both will generate CRCs that don't match the real controller
- The real controller's CRC algorithm must be determined before packets can be validated
