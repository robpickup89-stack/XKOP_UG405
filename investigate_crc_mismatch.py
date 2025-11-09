#!/usr/bin/env python3
"""
Investigate why Frame 69 CRC doesn't match even with the correct algorithm
"""

import sys
sys.path.insert(0, '/home/user/XKOP_UG405')

from windows_xkop_controller import CRC_TABLE

def xkop_crc_official(data: bytes) -> bytes:
    """Official CRC algorithm from spec"""
    crc1 = 0
    crc0 = 0
    for byte_val in data:
        temp = (crc1 ^ byte_val) & 0xFF
        crc1 = (crc0 ^ CRC_TABLE[temp]) & 0xFF
        crc0 = (CRC_TABLE[temp] >> 8) & 0xFF
    return bytes([crc1, crc0])

# Frame 69 packet
frame69 = bytes.fromhex("ca3500000000010001020001ff00009847")

print("="*80)
print("INVESTIGATING FRAME 69 CRC MISMATCH")
print("="*80)

print("\nHypothesis 1: Maybe the packet bytes are in a different order?")
print("-"*80)

# Try different byte orderings of the data
data = frame69[:15]
print(f"Original data: {data.hex().upper()}")
print(f"CRC: {xkop_crc_official(data).hex().upper()} (expected: 9847)")

# Maybe value bytes are swapped?
data_swapped = bytearray()
data_swapped.extend(frame69[:3])  # Header + type
for i in range(3, 15, 3):
    # Swap the two value bytes in each record
    data_swapped.append(frame69[i])      # index
    data_swapped.append(frame69[i+2])    # value LSB
    data_swapped.append(frame69[i+1])    # value MSB
swapped_data = bytes(data_swapped)
print(f"\nValue bytes swapped: {swapped_data.hex().upper()}")
print(f"CRC: {xkop_crc_official(swapped_data).hex().upper()} (expected: 9847)")

print("\n" + "="*80)
print("Hypothesis 2: Maybe the CRC bytes are stored in reverse order?")
print("-"*80)

calc_crc = xkop_crc_official(data)
recv_crc = frame69[15:17]
recv_crc_reversed = bytes([recv_crc[1], recv_crc[0]])

print(f"Calculated CRC: {calc_crc.hex().upper()}")
print(f"Received CRC: {recv_crc.hex().upper()}")
print(f"Received CRC reversed: {recv_crc_reversed.hex().upper()}")
print(f"Match with reversed: {calc_crc == recv_crc_reversed}")

print("\n" + "="*80)
print("Hypothesis 3: Let's build the packet ourselves and see what CRC we get")
print("-"*80)

# Build a packet with the same data
from windows_xkop_controller import xkop_build_data

# Frame 69 has: Index 0=0, Index 1=1, Index 2=1
records = [(0, 0), (1, 1), (2, 1)]
built_packet = xkop_build_data(records)

print(f"Frame 69 packet:  {frame69.hex().upper()}")
print(f"Built packet:     {built_packet.hex().upper()}")
print(f"Match: {built_packet == frame69}")

if built_packet != frame69:
    print("\nDifferences:")
    for i, (b1, b2) in enumerate(zip(frame69, built_packet)):
        if b1 != b2:
            print(f"  Byte {i}: Frame69={b1:02X}, Built={b2:02X}")

print("\n" + "="*80)
print("Hypothesis 4: What if the packet in Frame 69 is actually FROM the Pi?")
print("-"*80)

print("Frame 69 Wireshark info:")
print("  Src Port: 8001 (controller)")
print("  Dst Port: 59514 (client/Pi)")
print("  Direction: Controller → Pi")
print("\nSo this IS from the controller. But maybe the controller firmware")
print("has a different implementation than the spec document?")

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
print("""
The official CRC algorithm from the spec is correctly implemented, but
Frame 69's CRC doesn't match.

Possible explanations:
1. The Frame 69 packet is corrupted/modified
2. The controller firmware has a bug or different implementation
3. There's additional data included in the CRC we can't see
4. The spec document is outdated/incorrect

Next steps:
1. Can you capture MORE packets from the real controller?
2. Does the windows_xkop_controller.py simulator work with the real Pi?
3. Try the fixed app.py with packets from windows_xkop_controller.py
""")
print("="*80)
