#!/usr/bin/env python3
"""
CRC16 Reverse Engineering Tool
Tests multiple CRC16 algorithms to find which one matches the real controller
"""

import struct

# Test data from real controller packets
TEST_PACKETS = [
    {
        "name": "Frame 69",
        "data": bytes.fromhex("CA3500000000010001020001FF0000"),
        "crc": bytes.fromhex("9847"),
    },
    {
        "name": "Error Log Packet",
        "data": bytes.fromhex("CA3502000000000000000000000000"),
        "crc": bytes.fromhex("9BA0"),
    },
]

# Common CRC16 algorithms
class CRC16:
    """Collection of common CRC16 algorithms"""

    @staticmethod
    def _crc16_generic(data: bytes, poly: int, init: int, xor_out: int, ref_in: bool, ref_out: bool) -> int:
        """Generic CRC16 calculation"""
        def reflect(val: int, width: int) -> int:
            result = 0
            for i in range(width):
                if val & (1 << i):
                    result |= 1 << (width - 1 - i)
            return result

        crc = init
        for byte in data:
            if ref_in:
                byte = reflect(byte, 8)
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
                crc &= 0xFFFF

        if ref_out:
            crc = reflect(crc, 16)

        return crc ^ xor_out

    @staticmethod
    def ccitt_false(data: bytes) -> int:
        """CRC16-CCITT-FALSE (current implementation)"""
        return CRC16._crc16_generic(data, 0x1021, 0xFFFF, 0x0000, False, False)

    @staticmethod
    def xmodem(data: bytes) -> int:
        """CRC16-XMODEM"""
        return CRC16._crc16_generic(data, 0x1021, 0x0000, 0x0000, False, False)

    @staticmethod
    def modbus(data: bytes) -> int:
        """CRC16-MODBUS"""
        return CRC16._crc16_generic(data, 0x8005, 0xFFFF, 0x0000, True, True)

    @staticmethod
    def ibm(data: bytes) -> int:
        """CRC16-IBM / ARC"""
        return CRC16._crc16_generic(data, 0x8005, 0x0000, 0x0000, True, True)

    @staticmethod
    def ccitt_true(data: bytes) -> int:
        """CRC16-CCITT-TRUE / KERMIT"""
        return CRC16._crc16_generic(data, 0x1021, 0x0000, 0x0000, True, True)

    @staticmethod
    def dnp(data: bytes) -> int:
        """CRC16-DNP"""
        return CRC16._crc16_generic(data, 0x3D65, 0x0000, 0xFFFF, True, True)

    @staticmethod
    def x25(data: bytes) -> int:
        """CRC16-X25"""
        return CRC16._crc16_generic(data, 0x1021, 0xFFFF, 0xFFFF, True, True)

    @staticmethod
    def maxim(data: bytes) -> int:
        """CRC16-MAXIM"""
        return CRC16._crc16_generic(data, 0x8005, 0x0000, 0xFFFF, True, True)

    @staticmethod
    def usb(data: bytes) -> int:
        """CRC16-USB"""
        return CRC16._crc16_generic(data, 0x8005, 0xFFFF, 0xFFFF, True, True)

    @staticmethod
    def buypass(data: bytes) -> int:
        """CRC16-BUYPASS"""
        return CRC16._crc16_generic(data, 0x8005, 0x0000, 0x0000, False, False)

    @staticmethod
    def dds_110(data: bytes) -> int:
        """CRC16-DDS-110"""
        return CRC16._crc16_generic(data, 0x8005, 0x800D, 0x0000, False, False)

# List of all algorithms to test
ALGORITHMS = [
    ("CRC16-CCITT-FALSE (current)", CRC16.ccitt_false),
    ("CRC16-XMODEM", CRC16.xmodem),
    ("CRC16-MODBUS", CRC16.modbus),
    ("CRC16-IBM/ARC", CRC16.ibm),
    ("CRC16-CCITT-TRUE/KERMIT", CRC16.ccitt_true),
    ("CRC16-DNP", CRC16.dnp),
    ("CRC16-X25", CRC16.x25),
    ("CRC16-MAXIM", CRC16.maxim),
    ("CRC16-USB", CRC16.usb),
    ("CRC16-BUYPASS", CRC16.buypass),
    ("CRC16-DDS-110", CRC16.dds_110),
]

def test_all_algorithms():
    """Test all CRC16 algorithms against captured packets"""
    print("="*80)
    print("CRC16 REVERSE ENGINEERING TOOL")
    print("="*80)
    print("\nTesting multiple CRC16 algorithms against real controller packets...\n")

    results = {}

    for packet in TEST_PACKETS:
        print(f"\n{'='*80}")
        print(f"Testing: {packet['name']}")
        print(f"{'='*80}")
        print(f"Data (15 bytes): {packet['data'].hex().upper()}")
        print(f"Expected CRC:    {packet['crc'].hex().upper()}")

        # Get expected CRC as both byte orders
        crc_be = struct.unpack('>H', packet['crc'])[0]
        crc_le = struct.unpack('<H', packet['crc'])[0]
        print(f"  As big-endian:    0x{crc_be:04X}")
        print(f"  As little-endian: 0x{crc_le:04X}")

        print(f"\n{'Algorithm':<35} {'Calculated':<12} {'BE Match':<10} {'LE Match':<10}")
        print("-"*70)

        for name, func in ALGORITHMS:
            calc_crc = func(packet['data'])
            be_match = (calc_crc == crc_be)
            le_match = (calc_crc == crc_le)

            # Also check byte-swapped
            calc_crc_swapped = ((calc_crc & 0xFF) << 8) | ((calc_crc >> 8) & 0xFF)
            be_match_swapped = (calc_crc_swapped == crc_be)
            le_match_swapped = (calc_crc_swapped == crc_le)

            match_str_be = "✓ MATCH" if be_match else ("✓ SWAP" if be_match_swapped else "")
            match_str_le = "✓ MATCH" if le_match else ("✓ SWAP" if le_match_swapped else "")

            print(f"{name:<35} 0x{calc_crc:04X}       {match_str_be:<10} {match_str_le:<10}")

            # Track matches
            if be_match or le_match or be_match_swapped or le_match_swapped:
                if name not in results:
                    results[name] = []
                results[name].append(packet['name'])

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("="*80)

    if results:
        print("\nAlgorithms that matched one or more packets:")
        for alg, packets in results.items():
            print(f"\n{alg}:")
            for pkt in packets:
                print(f"  ✓ {pkt}")

        # Find algorithms that matched ALL packets
        all_match = [alg for alg, pkts in results.items() if len(pkts) == len(TEST_PACKETS)]
        if all_match:
            print(f"\n{'='*80}")
            print("RECOMMENDED ALGORITHMS (matched ALL test packets):")
            print("="*80)
            for alg in all_match:
                print(f"  ✓ {alg}")
        else:
            print(f"\n⚠️  No algorithm matched ALL test packets!")
            print("   More test data may be needed.")
    else:
        print("\n✗ NO MATCHES FOUND!")
        print("\nPossible reasons:")
        print("  1. The controller uses a custom CRC algorithm not in the standard list")
        print("  2. The CRC includes additional data (e.g., packet count, timestamp)")
        print("  3. The captured CRC bytes are corrupted or from a different protocol layer")
        print("\nRecommendations:")
        print("  - Capture more packets from the real controller")
        print("  - Use 'reveng' tool for more comprehensive CRC analysis")
        print("  - Contact the controller manufacturer for CRC specification")

    print("="*80)

if __name__ == "__main__":
    test_all_algorithms()
