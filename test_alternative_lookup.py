#!/usr/bin/env python3
"""
Test alternative lookup strategies - maybe we're using the wrong byte for table lookup
"""

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

# Test with all 5 packets
test_packets = [
    (bytes.fromhex("CA 35 02 00 00 00 00 00 00 00 00 00 00 00 00"), bytes.fromhex("9B A0")),
    (bytes.fromhex("CA 35 00 00 00 01 01 00 00 FF 00 00 FF 00 00"), bytes.fromhex("99 7C")),
    (bytes.fromhex("CA 35 00 03 00 01 FF 00 00 FF 00 00 FF 00 00"), bytes.fromhex("D6 90")),
    (bytes.fromhex("CA 35 00 01 00 01 FF 00 00 FF 00 00 FF 00 00"), bytes.fromhex("AF 4D")),
    (bytes.fromhex("CA 35 00 00 00 00 01 00 00 02 00 00 03 00 00"), bytes.fromhex("6F 31")),
]

def test_algorithm(name, func):
    """Test an algorithm against all packets"""
    matches = 0
    for data, expected in test_packets:
        result = func(data)
        if result == expected:
            matches += 1

    match_str = f"{matches}/{len(test_packets)} matches"
    status = "✓ ALL MATCH!" if matches == len(test_packets) else match_str
    print(f"{name:60} {status}")

    return matches == len(test_packets)

print("Testing alternative CRC algorithms:\n")
print("="*80)

# Algorithm 1: Use crc0 instead of crc1 for lookup
def alg1(data):
    crc1 = 0
    crc0 = 0
    for byte_val in data:
        temp = (crc0 ^ byte_val) & 0xFF  # Use crc0!
        crc0 = (crc1 ^ CRC_TABLE[temp]) & 0xFF  # Swap assignment
        crc1 = (CRC_TABLE[temp] >> 8) & 0xFF
    return bytes([crc1, crc0])

# Algorithm 2: Same as alg1 but swapped output
def alg2(data):
    crc1 = 0
    crc0 = 0
    for byte_val in data:
        temp = (crc0 ^ byte_val) & 0xFF
        crc0 = (crc1 ^ CRC_TABLE[temp]) & 0xFF
        crc1 = (CRC_TABLE[temp] >> 8) & 0xFF
    return bytes([crc0, crc1])

# Algorithm 3: Different assignment order
def alg3(data):
    crc1 = 0
    crc0 = 0
    for byte_val in data:
        temp = (crc0 ^ byte_val) & 0xFF
        new_crc1 = (CRC_TABLE[temp] >> 8) & 0xFF
        new_crc0 = (crc1 ^ CRC_TABLE[temp]) & 0xFF
        crc1 = new_crc1
        crc0 = new_crc0
    return bytes([crc1, crc0])

# Algorithm 4: Same as alg3 but swapped output
def alg4(data):
    crc1 = 0
    crc0 = 0
    for byte_val in data:
        temp = (crc0 ^ byte_val) & 0xFF
        new_crc1 = (CRC_TABLE[temp] >> 8) & 0xFF
        new_crc0 = (crc1 ^ CRC_TABLE[temp]) & 0xFF
        crc1 = new_crc1
        crc0 = new_crc0
    return bytes([crc0, crc1])

# Algorithm 5: Use table value low byte for crc1
def alg5(data):
    crc1 = 0
    crc0 = 0
    for byte_val in data:
        temp = (crc1 ^ byte_val) & 0xFF
        crc0 = (crc1 ^ (CRC_TABLE[temp] >> 8)) & 0xFF
        crc1 = (crc0 ^ CRC_TABLE[temp]) & 0xFF
    return bytes([crc1, crc0])

# Algorithm 6: Process as 16-bit CRC
def alg6(data):
    crc = 0
    for byte_val in data:
        temp = ((crc >> 8) ^ byte_val) & 0xFF
        crc = ((crc << 8) ^ CRC_TABLE[temp]) & 0xFFFF
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF])

# Algorithm 7: Same as alg6 but use low byte for lookup
def alg7(data):
    crc = 0
    for byte_val in data:
        temp = (crc ^ byte_val) & 0xFF
        crc = ((crc >> 8) ^ CRC_TABLE[temp]) & 0xFFFF
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF])

# Algorithm 8: alg7 with swapped output
def alg8(data):
    crc = 0
    for byte_val in data:
        temp = (crc ^ byte_val) & 0xFF
        crc = ((crc >> 8) ^ CRC_TABLE[temp]) & 0xFFFF
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])

algorithms = [
    ("ALG1: Use crc0 for lookup, crc1 XOR table", alg1),
    ("ALG2: ALG1 with swapped output", alg2),
    ("ALG3: Use crc0 lookup, crc1 XOR table (ordered assignment)", alg3),
    ("ALG4: ALG3 with swapped output", alg4),
    ("ALG5: Special crc0/crc1 swap during loop", alg5),
    ("ALG6: 16-bit CRC with high byte lookup", alg6),
    ("ALG7: 16-bit CRC with low byte lookup", alg7),
    ("ALG8: ALG7 with swapped output", alg8),
]

for name, func in algorithms:
    if test_algorithm(name, func):
        print("\n" + "="*80)
        print("🎯 SOLUTION FOUND!")
        print("="*80)
        print(f"Algorithm: {name}\n")

        # Show detailed results
        for i, (data, expected) in enumerate(test_packets, 1):
            result = func(data)
            print(f"Packet {i}:")
            print(f"  Data:     {' '.join(f'{b:02X}' for b in data)}")
            print(f"  Expected: {' '.join(f'{b:02X}' for b in expected)}")
            print(f"  Got:      {' '.join(f'{b:02X}' for b in result)}")
            print(f"  Match:    {'✓' if result == expected else '✗'}\n")
        break

print("="*80)
