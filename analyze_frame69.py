#!/usr/bin/env python3
"""Analyze Frame 69 packet capture data"""

import sys
sys.path.insert(0, '/home/user/XKOP_UG405')
from windows_xkop_controller import xkop_crc16_write, xkop_crc16_check, parse_xkop_packet, print_packet_info

# TCP payload from Frame 69
tcp_payload = bytes.fromhex("ca3500000000010001020001ff00009847")

# What was received according to the error message
received_data = bytes.fromhex("CA35020000000000000000000000009BA0")

print("="*70)
print("FRAME 69 PACKET ANALYSIS")
print("="*70)

print("\n1. TCP PAYLOAD FROM WIRESHARK:")
print_packet_info(tcp_payload, "TCP Payload")

print("\n" + "="*70)
print("\n2. DATA RECEIVED BY PARSER (according to error message):")
print_packet_info(received_data, "Received Data")

print("\n" + "="*70)
print("\n3. MANUAL CRC VERIFICATION:")

# Verify TCP payload CRC
tcp_crc_valid = xkop_crc16_check(tcp_payload)
print(f"\nTCP Payload CRC valid: {tcp_crc_valid}")

# Calculate expected CRC for TCP payload (first 15 bytes)
tcp_data = tcp_payload[:15]
tcp_expected_crc = xkop_crc16_write(tcp_data)
tcp_actual_crc = tcp_payload[15:17]
print(f"  Data (15 bytes): {tcp_data.hex().upper()}")
print(f"  Expected CRC: {tcp_expected_crc.hex().upper()}")
print(f"  Actual CRC:   {tcp_actual_crc.hex().upper()}")
print(f"  Match: {tcp_expected_crc == tcp_actual_crc}")

# Verify received data CRC
received_crc_valid = xkop_crc16_check(received_data)
print(f"\nReceived Data CRC valid: {received_crc_valid}")

# Calculate expected CRC for received data (first 15 bytes)
received_data_part = received_data[:15]
received_expected_crc = xkop_crc16_write(received_data_part)
received_actual_crc = received_data[15:17]
print(f"  Data (15 bytes): {received_data_part.hex().upper()}")
print(f"  Expected CRC: {received_expected_crc.hex().upper()}")
print(f"  Actual CRC:   {received_actual_crc.hex().upper()}")
print(f"  Match: {received_expected_crc == received_actual_crc}")

print("\n" + "="*70)
print("\n4. KEY DIFFERENCES:")
print(f"  Type field: TCP=0x{tcp_payload[2]:02X} vs Received=0x{received_data[2]:02X}")
print(f"  CRC bytes: TCP={tcp_payload[15:17].hex().upper()} vs Received={received_data[15:17].hex().upper()}")

print("\n" + "="*70)
print("\n5. ANALYSIS:")
print("  The TCP payload and received data are COMPLETELY DIFFERENT packets!")
print("  - TCP payload has Type 0x00 (DATA)")
print("  - Received has Type 0x02 (STATUS)")
print("  - Different record data")
print("  - Different CRC values")
print("\n  This suggests the parser is receiving a different packet than")
print("  what was sent in Frame 69, possibly from a different frame or")
print("  there's a packet ordering/buffering issue.")
print("="*70)
