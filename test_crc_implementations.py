#!/usr/bin/env python3
"""Test different CRC implementations to find the mismatch"""

import struct
import sys
sys.path.insert(0, '/home/user/XKOP_UG405')

# Import the CRC table
from windows_xkop_controller import CRC_TABLE

def xkop_crc_int(data: bytes) -> int:
    """CRC implementation from app.py and test_xkop_tcp.py"""
    crc = 0
    for b in data:
        t = CRC_TABLE[(crc ^ b) & 0xFF]
        crc = ((crc >> 8) ^ t) & 0xFFFF
    return crc

def xkop_crc16_write(data: bytes) -> bytes:
    """CRC implementation from windows_xkop_controller.py"""
    crc1 = 0
    crc0 = 0

    for byte_val in data:
        temp = (crc1 ^ byte_val) & 0xFF
        crc1 = (crc0 ^ CRC_TABLE[temp]) & 0xFF
        crc0 = (CRC_TABLE[temp] >> 8) & 0xFF

    return bytes([crc1, crc0])

# Test packet from Frame 69 (first 15 bytes, without CRC)
tcp_data = bytes.fromhex("ca3500000000010001020001ff0000")
tcp_full = bytes.fromhex("ca3500000000010001020001ff00009847")

print("="*70)
print("CRC IMPLEMENTATION COMPARISON")
print("="*70)

print(f"\nTest data (15 bytes): {tcp_data.hex().upper()}")
print(f"Full packet (17 bytes): {tcp_full.hex().upper()}")

# Method 1: Integer CRC with big-endian packing (test_xkop_tcp.py style)
crc_int = xkop_crc_int(tcp_data)
crc_big_endian = struct.pack(">H", crc_int)
print(f"\n1. Integer CRC (big-endian pack):")
print(f"   CRC int: 0x{crc_int:04X}")
print(f"   Packed:  {crc_big_endian.hex().upper()}")

# Method 2: Integer CRC with little-endian packing (app.py style)
crc_little_endian = struct.pack("<H", crc_int)
print(f"\n2. Integer CRC (little-endian pack):")
print(f"   CRC int: 0x{crc_int:04X}")
print(f"   Packed:  {crc_little_endian.hex().upper()}")

# Method 3: Windows controller style (byte array)
crc_bytes = xkop_crc16_write(tcp_data)
print(f"\n3. Windows controller CRC (bytes):")
print(f"   Packed:  {crc_bytes.hex().upper()}")

# What's in the actual packet?
actual_crc = tcp_full[15:17]
print(f"\n4. Actual CRC in Frame 69:")
print(f"   Bytes:   {actual_crc.hex().upper()}")
print(f"   As BE:   0x{struct.unpack('>H', actual_crc)[0]:04X}")
print(f"   As LE:   0x{struct.unpack('<H', actual_crc)[0]:04X}")

print("\n" + "="*70)
print("MATCHES:")
print(f"  Big-endian matches actual:    {crc_big_endian == actual_crc}")
print(f"  Little-endian matches actual: {crc_little_endian == actual_crc}")
print(f"  Windows style matches actual: {crc_bytes == actual_crc}")
print("="*70)

# Now test if the packet is valid with different interpretations
print("\n" + "="*70)
print("VALIDATION TEST:")

# Check with app.py's method (little-endian unpack)
try:
    calc_int = xkop_crc_int(tcp_full[:15])
    recv_le = struct.unpack("<H", tcp_full[15:17])[0]
    print(f"\napp.py method (little-endian):")
    print(f"  Calculated: 0x{calc_int:04X}")
    print(f"  Received:   0x{recv_le:04X}")
    print(f"  Match: {calc_int == recv_le}")
except Exception as e:
    print(f"  Error: {e}")

# Check with test_xkop_tcp.py's method (big-endian unpack)
try:
    calc_int = xkop_crc_int(tcp_full[:15])
    recv_be = struct.unpack(">H", tcp_full[15:17])[0]
    print(f"\ntest_xkop_tcp.py method (big-endian):")
    print(f"  Calculated: 0x{calc_int:04X}")
    print(f"  Received:   0x{recv_be:04X}")
    print(f"  Match: {calc_int == recv_be}")
except Exception as e:
    print(f"  Error: {e}")

print("="*70)
