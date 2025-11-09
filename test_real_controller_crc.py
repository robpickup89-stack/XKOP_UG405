#!/usr/bin/env python3
"""
Test CRC algorithms with actual packets from the real controller logs
"""

import struct

# Test data from real controller at IP 10.164.95.208
# Format: (data_hex, crc_hex, description)
TEST_PACKETS = [
    ("CA 35 02 00 00 00 00 00 00 00 00 00 00 00 00", "9B A0", "Alive message (type 0x02)"),
    ("CA 35 00 00 00 01 01 00 00 FF 00 00 FF 00 00", "99 7C", "Data message 1"),
    ("CA 35 00 03 00 01 FF 00 00 FF 00 00 FF 00 00", "D6 90", "Data message 2"),
    ("CA 35 00 01 00 01 FF 00 00 FF 00 00 FF 00 00", "AF 4D", "Data message 3"),
    ("CA 35 00 00 00 00 01 00 00 02 00 00 03 00 00", "6F 31", "Data message 4"),
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
        """CRC16-CCITT-FALSE"""
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
    ("CRC16-CCITT-FALSE", CRC16.ccitt_false),
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
    print("REAL CONTROLLER CRC ANALYSIS")
    print("="*80)
    print(f"\nAnalyzing {len(TEST_PACKETS)} packets from controller at 10.164.95.208:8001\n")

    results = {}
    matches_per_algorithm = {}

    for data_hex, crc_hex, desc in TEST_PACKETS:
        data = bytes.fromhex(data_hex.replace(" ", ""))
        crc_bytes = bytes.fromhex(crc_hex.replace(" ", ""))

        print(f"\n{'='*80}")
        print(f"Packet: {desc}")
        print(f"{'='*80}")
        print(f"Data: {data_hex}")
        print(f"CRC:  {crc_hex}")

        # Get expected CRC as both byte orders
        crc_as_received = (crc_bytes[0] << 8) | crc_bytes[1]  # As two bytes
        crc_swapped = (crc_bytes[1] << 8) | crc_bytes[0]

        print(f"\nExpected CRC:")
        print(f"  Bytes [0x{crc_bytes[0]:02X}, 0x{crc_bytes[1]:02X}] = 0x{crc_as_received:04X}")
        print(f"  Swapped:                       0x{crc_swapped:04X}")

        print(f"\n{'Algorithm':<30} {'Calculated':<12} {'Match':<15}")
        print("-"*60)

        found_match = False
        for name, func in ALGORITHMS:
            calc_crc = func(data)

            # Check both byte orders
            match_type = ""
            if calc_crc == crc_as_received:
                match_type = "✓ EXACT"
                found_match = True
            elif calc_crc == crc_swapped:
                match_type = "✓ SWAPPED"
                found_match = True

            print(f"{name:<30} 0x{calc_crc:04X}       {match_type:<15}")

            if match_type:
                if name not in results:
                    results[name] = []
                results[name].append((desc, match_type))
                matches_per_algorithm[name] = matches_per_algorithm.get(name, 0) + 1

        if not found_match:
            print(f"\n⚠️  No standard algorithm matched this packet!")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("="*80)

    if results:
        print("\n✓ Algorithms that matched one or more packets:\n")
        for alg in sorted(results.keys(), key=lambda x: matches_per_algorithm.get(x, 0), reverse=True):
            count = matches_per_algorithm[alg]
            total = len(TEST_PACKETS)
            percentage = (count / total) * 100
            print(f"{alg}: {count}/{total} matches ({percentage:.0f}%)")
            for pkt_desc, match_type in results[alg]:
                print(f"  {match_type} - {pkt_desc}")
            print()

        # Find algorithms that matched ALL packets
        all_match = [alg for alg, count in matches_per_algorithm.items() if count == len(TEST_PACKETS)]
        if all_match:
            print(f"{'='*80}")
            print("🎯 SOLUTION FOUND! These algorithms matched ALL packets:")
            print("="*80)
            for alg in all_match:
                print(f"  ✓ {alg}")
                if results[alg]:
                    match_type = results[alg][0][1]
                    if "SWAPPED" in match_type:
                        print(f"    NOTE: Requires byte swapping (reverse output order)")
            print()
        else:
            print(f"⚠️  No single algorithm matched ALL packets.")
            print(f"   The controller may use a custom CRC or include additional data.\n")
    else:
        print("\n✗ NO MATCHES FOUND with any standard CRC16 algorithm!")
        print("\nPossible reasons:")
        print("  1. Custom/proprietary CRC algorithm")
        print("  2. CRC includes additional data (sequence, timestamp, etc.)")
        print("  3. Different protocol layer (e.g., not XKOP CRC)")
        print("\nNext steps:")
        print("  - Try CRC RevEng tool: reveng -w 16 -s [data] [crc]")
        print("  - Contact controller manufacturer")
        print("  - Disable CRC validation temporarily for testing")

    print("="*80)

if __name__ == "__main__":
    test_all_algorithms()
