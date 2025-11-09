#!/usr/bin/env python3
"""
Test script to demonstrate READ/WRITE functionality of XKOP controller
"""

import sys
sys.path.insert(0, '/home/user/XKOP_UG405')

from windows_xkop_controller import parse_xkop_packet, xkop_build_data

def test_packet_from_wireshark():
    """Test the exact packet from Wireshark capture"""
    print("="*70)
    print("ANALYZING WIRESHARK PACKET")
    print("="*70)

    # The packet from your Wireshark capture
    packet_hex = "ca35000000000100010200000300006101"
    packet = bytes.fromhex(packet_hex)

    print(f"\nPacket (hex): {packet_hex}")
    print(f"Packet (bytes): {' '.join(f'{b:02X}' for b in packet)}")
    print(f"Length: {len(packet)} bytes")

    # Parse it
    parsed = parse_xkop_packet(packet)

    print(f"\n{'─'*70}")
    print("PARSED STRUCTURE:")
    print(f"{'─'*70}")
    print(f"Header:    {parsed['header1']} {parsed['header2']}")
    print(f"Type:      {parsed['type']} (DATA)")
    print(f"CRC:       {parsed['crc']} - {'✓ VALID' if parsed['valid_crc'] else '✗ INVALID'}")
    print(f"\nRecords ({len(parsed['records'])}):")

    for rec in parsed['records']:
        print(f"  Index {rec['index']:3d} = {rec['value']:5d} (0x{rec['value']:04X})")

    # Determine READ vs WRITE
    is_write = any(rec["value"] != 0 for rec in parsed["records"])

    print(f"\n{'─'*70}")
    print(f"OPERATION TYPE: {'WRITE' if is_write else 'READ'}")
    print(f"{'─'*70}")

    if is_write:
        print("\n✓ This packet WILL SET VALUES (WRITE operation)")
        print("  The controller will:")
        print("  1. Store the values sent by client:")
        for rec in parsed["records"]:
            print(f"     • index_values[{rec['index']}] = {rec['value']}")
        print("  2. Send back an ACK with the same values")
    else:
        print("\n→ This packet is a READ REQUEST")
        print("  The controller will:")
        print("  1. Read current values for these indices")
        print("  2. Send back a response with stored values")

    print()

def test_read_write_examples():
    """Show examples of READ vs WRITE packets"""
    print("\n" + "="*70)
    print("READ vs WRITE EXAMPLES")
    print("="*70)

    # WRITE example
    print("\n1. WRITE OPERATION (set Index 0=100, Index 1=200):")
    write_packet = xkop_build_data([(0, 100), (1, 200)])
    print(f"   Hex: {write_packet.hex()}")
    parsed = parse_xkop_packet(write_packet)
    print(f"   Records: ", end="")
    for rec in parsed['records']:
        print(f"Index {rec['index']}={rec['value']} ", end="")
    print("\n   → Controller STORES: index_values[0]=100, index_values[1]=200")

    # READ example
    print("\n2. READ OPERATION (request Index 0, Index 1):")
    read_packet = xkop_build_data([(0, 0), (1, 0)])
    print(f"   Hex: {read_packet.hex()}")
    parsed = parse_xkop_packet(read_packet)
    print(f"   Records: ", end="")
    for rec in parsed['records']:
        print(f"Index {rec['index']}={rec['value']} ", end="")
    print("\n   → Controller RETURNS: current values of index[0] and index[1]")

    print()

if __name__ == "__main__":
    test_packet_from_wireshark()
    test_read_write_examples()

    print("="*70)
    print("SUMMARY")
    print("="*70)
    print("The controller now supports BOTH read and write:")
    print("  • WRITE: Client sends non-zero values → Controller stores them")
    print("  • READ:  Client sends zero values → Controller returns current values")
    print("="*70)
