#!/usr/bin/env python3
"""Test CRC calculation with actual packet data from logs"""

CRC_TABLE = [
    0x0000, 0x0f89, 0x1f12, 0x109b, 0x3e24, 0x31ad, 0x2136, 0x2ebf,
    0x7c48, 0x73c1, 0x635a, 0x6cd3, 0x426c, 0x4de5, 0x5d7e, 0x52f7,
    0xf081, 0xff08, 0xef93, 0xe01a, 0xcea5, 0xc12c, 0xd1b7, 0xde3e,
    0x8cc9, 0x8340, 0x93db, 0x9c52, 0xb2ed, 0xbd64, 0xadff, 0xa276,
    0xe102, 0xee8b, 0xfe10, 0xf199, 0xdf26, 0xd0af, 0xc034, 0xcfbd,
    0x9d4a, 0x92c3, 0x8258, 0x8dd1, 0xa36e, 0xace7, 0xbc7c, 0xb3f5,
    0x1183, 0x1e0a, 0x0e91, 0x0118, 0x2fa7, 0x202e, 0x30b5, 0x3f3c,
    0x6dcb, 0x6242, 0x72d9, 0x7d50, 0x53ef, 0x5c66, 0x4cfd, 0x4374,
    0xc204, 0xcd8d, 0xdd16, 0xd29f, 0xfc20, 0xf3a9, 0xe332, 0xecbb,
    0xbe4c, 0xb1c5, 0xa15e, 0xaed7, 0x8068, 0x8fe1, 0x9f7a, 0x90f3,
    0x3285, 0x3d0c, 0x2d97, 0x221e, 0x0ca1, 0x0328, 0x13b3, 0x1c3a,
    0x4ecd, 0x4144, 0x51df, 0x5e56, 0x70e9, 0x7f60, 0x6ffb, 0x6072,
    0x2306, 0x2c8f, 0x3c14, 0x339d, 0x1d22, 0x12ab, 0x0230, 0x0db9,
    0x5f4e, 0x50c7, 0x405c, 0x4fd5, 0x616a, 0x6ee3, 0x7e78, 0x71f1,
    0xd387, 0xdc0e, 0xcc95, 0xc31c, 0xeda3, 0xe22a, 0xf2b1, 0xfd38,
    0xafcf, 0xa046, 0xb0dd, 0xbf54, 0x91eb, 0x9e62, 0x8ef9, 0x8170,
    0x8408, 0x8b81, 0x9b1a, 0x9493, 0xba2c, 0xb5a5, 0xa53e, 0xaab7,
    0xf840, 0xf7c9, 0xe752, 0xe8db, 0xc664, 0xc9ed, 0xd976, 0xd6ff,
    0x7489, 0x7b00, 0x6b9b, 0x6412, 0x4aad, 0x4524, 0x55bf, 0x5a36,
    0x08c1, 0x0748, 0x17d3, 0x185a, 0x36e5, 0x396c, 0x29f7, 0x267e,
    0x650a, 0x6a83, 0x7a18, 0x7591, 0x5b2e, 0x54a7, 0x443c, 0x4bb5,
    0x1942, 0x16cb, 0x0650, 0x09d9, 0x2766, 0x28ef, 0x3874, 0x37fd,
    0x958b, 0x9a02, 0x8a99, 0x8510, 0xabaf, 0xa426, 0xb4bd, 0xbb34,
    0xe9c3, 0xe64a, 0xf6d1, 0xf958, 0xd7e7, 0xd86e, 0xc8f5, 0xc77c,
    0x460c, 0x4985, 0x591e, 0x5697, 0x7828, 0x77a1, 0x673a, 0x68b3,
    0x3a44, 0x35cd, 0x2556, 0x2adf, 0x0460, 0x0be9, 0x1b72, 0x14fb,
    0xb68d, 0xb904, 0xa99f, 0xa616, 0x88a9, 0x8720, 0x97bb, 0x9832,
    0xcac5, 0xc54c, 0xd5d7, 0xda5e, 0xf4e1, 0xfb68, 0xebf3, 0xe47a,
    0xa70e, 0xa887, 0xb81c, 0xb795, 0x992a, 0x96a3, 0x8638, 0x89b1,
    0xdb46, 0xd4cf, 0xc454, 0xcbdd, 0xe562, 0xeaeb, 0xfa70, 0xf5f9,
    0x578f, 0x5806, 0x489d, 0x4714, 0x69ab, 0x6622, 0x76b9, 0x7930,
    0x2bc7, 0x244e, 0x34d5, 0x3b5c, 0x15e3, 0x1a6a, 0x0af1, 0x0578,
]

def current_crc(data: bytes) -> bytes:
    """Current implementation from app.py"""
    crc1 = 0
    crc0 = 0

    for byte_val in data:
        temp = (crc1 ^ byte_val) & 0xFF
        crc1 = (crc0 ^ CRC_TABLE[temp]) & 0xFF
        crc0 = (CRC_TABLE[temp] >> 8) & 0xFF

    return bytes([crc1, crc0])

def crc_check_full_packet(packet: bytes) -> bool:
    """Check if CRC is valid by processing full packet"""
    crc1 = 0
    crc0 = 0

    for byte_val in packet:
        temp = (crc1 ^ byte_val) & 0xFF
        crc1 = (crc0 ^ CRC_TABLE[temp]) & 0xFF
        crc0 = (CRC_TABLE[temp] >> 8) & 0xFF

    return (crc1 == 0) and (crc0 == 0)

# Test packets from the logs
test_packets = [
    # (data bytes, expected CRC bytes)
    (bytes.fromhex("CA 35 02 00 00 00 00 00 00 00 00 00 00 00 00"), bytes.fromhex("9B A0")),
    (bytes.fromhex("CA 35 00 00 00 01 01 00 00 FF 00 00 FF 00 00"), bytes.fromhex("99 7C")),
    (bytes.fromhex("CA 35 00 03 00 01 FF 00 00 FF 00 00 FF 00 00"), bytes.fromhex("D6 90")),
    (bytes.fromhex("CA 35 00 01 00 01 FF 00 00 FF 00 00 FF 00 00"), bytes.fromhex("AF 4D")),
    (bytes.fromhex("CA 35 00 00 00 00 01 00 00 02 00 00 03 00 00"), bytes.fromhex("6F 31")),
]

print("Testing CRC calculations:")
print("=" * 80)

for i, (data, expected_crc) in enumerate(test_packets, 1):
    calc_crc = current_crc(data)

    print(f"\nPacket {i}:")
    print(f"  Data:     {' '.join(f'{b:02X}' for b in data)}")
    print(f"  Expected: {' '.join(f'{b:02X}' for b in expected_crc)}")
    print(f"  Current:  {' '.join(f'{b:02X}' for b in calc_crc)}")
    print(f"  Match:    {'✓ YES' if calc_crc == expected_crc else '✗ NO'}")

    # Test full packet check
    full_packet = data + expected_crc
    is_valid = crc_check_full_packet(full_packet)
    print(f"  Full packet check: {'✓ VALID' if is_valid else '✗ INVALID'}")

print("\n" + "=" * 80)
print("\nAnalysis: Testing byte order variations...")
print("=" * 80)

# Test byte order variations
data = bytes.fromhex("CA 35 02 00 00 00 00 00 00 00 00 00 00 00 00")
expected = bytes.fromhex("9B A0")

# Try reversed byte order
def crc_reversed_output(data: bytes) -> bytes:
    """Try reversing the output byte order"""
    crc1 = 0
    crc0 = 0

    for byte_val in data:
        temp = (crc1 ^ byte_val) & 0xFF
        crc1 = (crc0 ^ CRC_TABLE[temp]) & 0xFF
        crc0 = (CRC_TABLE[temp] >> 8) & 0xFF

    return bytes([crc0, crc1])  # Reversed!

calc_reversed = crc_reversed_output(data)
print(f"\nReversed output [crc0, crc1]:")
print(f"  Expected: {' '.join(f'{b:02X}' for b in expected)}")
print(f"  Calc:     {' '.join(f'{b:02X}' for b in calc_reversed)}")
print(f"  Match:    {'✓ YES' if calc_reversed == expected else '✗ NO'}")

# Try swapping crc0/crc1 in algorithm
def crc_swapped_vars(data: bytes) -> bytes:
    """Try swapping which variable is which"""
    crc0 = 0
    crc1 = 0

    for byte_val in data:
        temp = (crc0 ^ byte_val) & 0xFF  # Use crc0 instead of crc1
        crc0 = (crc1 ^ CRC_TABLE[temp]) & 0xFF  # Swap
        crc1 = (CRC_TABLE[temp] >> 8) & 0xFF

    return bytes([crc0, crc1])

calc_swapped = crc_swapped_vars(data)
print(f"\nSwapped algorithm variables:")
print(f"  Expected: {' '.join(f'{b:02X}' for b in expected)}")
print(f"  Calc:     {' '.join(f'{b:02X}' for b in calc_swapped)}")
print(f"  Match:    {'✓ YES' if calc_swapped == expected else '✗ NO'}")
