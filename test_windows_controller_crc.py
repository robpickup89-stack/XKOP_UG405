#!/usr/bin/env python3
"""Test if windows_xkop_controller.py CRC algorithm matches the packets"""

import sys
sys.path.insert(0, '/home/user/XKOP_UG405')

from windows_xkop_controller import xkop_crc16_write, xkop_build_data

print("="*70)
print("TESTING WINDOWS CONTROLLER CRC ALGORITHM")
print("="*70)

# Frame 69 should have records: Index 0=0, Index 1=1, Index 2=1
print("\nBuilding Frame 69 equivalent packet:")
print("  Records: (0, 0), (1, 1), (2, 1)")

records = [(0, 0), (1, 1), (2, 1)]
built_packet = xkop_build_data(records)

print(f"\nBuilt packet: {built_packet.hex().upper()}")
print(f"Frame 69:     CA3500000000010001020001FF00009847")
print(f"Match: {built_packet.hex().upper() == 'CA3500000000010001020001FF00009847'}")

# Parse the built packet
print(f"\nBreakdown of built packet:")
print(f"  Header: {built_packet[0:3].hex().upper()}")
print(f"  Records: {built_packet[3:15].hex().upper()}")
print(f"  CRC: {built_packet[15:17].hex().upper()}")

# Now test the CRC calculation
print("\n" + "="*70)
print("MANUAL CRC CALCULATION FOR FRAME 69 DATA")
print("="*70)

frame69_data = bytes.fromhex("CA3500000000010001020001FF0000")
frame69_crc = xkop_crc16_write(frame69_data)

print(f"Data (15 bytes): {frame69_data.hex().upper()}")
print(f"Calculated CRC:  {frame69_crc.hex().upper()}")
print(f"Frame 69 CRC:    9847")
print(f"Match: {frame69_crc.hex().upper() == '9847'}")

# Test with the error log packet
print("\n" + "="*70)
print("MANUAL CRC CALCULATION FOR ERROR LOG PACKET")
print("="*70)

error_data = bytes.fromhex("CA3502000000000000000000000000")
error_crc = xkop_crc16_write(error_data)

print(f"Data (15 bytes): {error_data.hex().upper()}")
print(f"Calculated CRC:  {error_crc.hex().upper()}")
print(f"Error log CRC:   9BA0")
print(f"Match: {error_crc.hex().upper() == '9BA0'}")

print("\n" + "="*70)
