#!/usr/bin/env python3
"""Complete analysis of Frame 69 and error log discrepancy"""

import struct
import sys
sys.path.insert(0, '/home/user/XKOP_UG405')

from windows_xkop_controller import CRC_TABLE

def xkop_crc_int(data: bytes) -> int:
    """CRC implementation from app.py"""
    crc = 0
    for b in data:
        t = CRC_TABLE[(crc ^ b) & 0xFF]
        crc = ((crc >> 8) ^ t) & 0xFFFF
    return crc

def analyze_packet(packet: bytes, name: str):
    """Analyze a packet and show all details"""
    print(f"\n{'='*70}")
    print(f"{name}")
    print(f"{'='*70}")
    print(f"Raw hex: {packet.hex().upper()}")
    print(f"Length: {len(packet)} bytes")

    if len(packet) != 17:
        print(f"ERROR: Invalid length!")
        return

    # Parse header
    print(f"\nHeader:")
    print(f"  HDR1: 0x{packet[0]:02X} ({'OK' if packet[0] == 0xCA else 'WRONG'})")
    print(f"  HDR2: 0x{packet[1]:02X} ({'OK' if packet[1] == 0x35 else 'WRONG'})")
    msg_type = packet[2]
    type_name = {0x00: 'DATA', 0x02: 'STATUS'}.get(msg_type, 'UNKNOWN')
    print(f"  Type: 0x{msg_type:02X} ({type_name})")

    # Parse records
    print(f"\nRecords:")
    for i in range(4):
        offset = 3 + (i * 3)
        idx = packet[offset]
        val = (packet[offset + 1] << 8) | packet[offset + 2]
        if idx != 0xFF:
            print(f"  Record {i+1}: Index {idx:3d} = {val:5d} (0x{val:04X})")
        else:
            print(f"  Record {i+1}: Empty")

    # Parse CRC
    crc_bytes = packet[15:17]
    print(f"\nCRC bytes: {crc_bytes.hex().upper()}")
    print(f"  As big-endian:    0x{struct.unpack('>H', crc_bytes)[0]:04X}")
    print(f"  As little-endian: 0x{struct.unpack('<H', crc_bytes)[0]:04X}")

    # Validate CRC
    data = packet[:15]
    calc_crc = xkop_crc_int(data)
    recv_crc_le = struct.unpack('<H', crc_bytes)[0]
    recv_crc_be = struct.unpack('>H', crc_bytes)[0]

    print(f"\nCRC Validation:")
    print(f"  Calculated CRC:           0x{calc_crc:04X}")
    print(f"  Received (little-endian): 0x{recv_crc_le:04X} {'✓ MATCH' if calc_crc == recv_crc_le else '✗ MISMATCH'}")
    print(f"  Received (big-endian):    0x{recv_crc_be:04X} {'✓ MATCH' if calc_crc == recv_crc_be else '✗ MISMATCH'}")

    # What app.py would do (little-endian)
    if calc_crc != recv_crc_le:
        print(f"\napp.py would REJECT this packet:")
        print(f"  Parse fail: CRC mismatch calc=0x{calc_crc:04X} recv=0x{recv_crc_le:04X}")

print("="*70)
print("FRAME 69 AND ERROR LOG ANALYSIS")
print("="*70)

# Frame 69 from Wireshark
frame69 = bytes.fromhex("ca3500000000010001020001ff00009847")
analyze_packet(frame69, "FRAME 69 - TCP Payload from Wireshark")

# Packet from error log
error_packet = bytes.fromhex("CA35020000000000000000000000009BA0")
analyze_packet(error_packet, "ERROR LOG PACKET - What was received")

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("""
These are TWO DIFFERENT PACKETS from different times!

Frame 69 has:
  - Type 0x00 (DATA)
  - Records: Index 0=0, Index 1=1, Index 2=1
  - INVALID CRC (should be 0x508E but is 0x9847)

Error log packet has:
  - Type 0x02 (STATUS)
  - All empty records
  - INVALID CRC (should be 0x5369 but is 0x9BA0)

BOTH packets have INVALID CRCs!

The controller is generating packets with WRONG CRCs.
This indicates the controller is using a different CRC algorithm
or byte ordering than what's expected by the parser.
""")
print("="*70)
