#!/usr/bin/env python3
"""
XKOP Test Client for Windows
Send and receive XKOP messages via UDP

Usage:
    python xkop_test_client.py --host 10.164.95.201 --port 8001
"""

import socket
import struct
import sys
import argparse
import time

# XKOP Protocol Constants
XKOP_HDR1 = 0xCA
XKOP_HDR2 = 0x35
XKOP_TYPE_DATA = 0x00

# CRC16 Lookup Table (same as server)
CRC_TABLE = [
    0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
    0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
    0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
    0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
    0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
    0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
    0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
    0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
    0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
    0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
    0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
    0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
    0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
    0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
    0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
    0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
    0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
    0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
    0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
    0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
    0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
    0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
    0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
    0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
    0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
    0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
    0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
    0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
    0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
    0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
    0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
    0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040
]

def xkop_crc(data: bytes) -> int:
    """Calculate CRC16 checksum for XKOP message"""
    crc = 0
    for b in data:
        t = CRC_TABLE[(crc ^ b) & 0xFF]
        crc = ((crc >> 8) ^ t) & 0xFFFF
    return crc

def xkop_build_data(records: list) -> bytes:
    """
    Build XKOP data message

    Args:
        records: List of (index, value) tuples, max 4 records
                 index: 0-254 (0xFF reserved for empty)
                 value: 0-65535

    Returns:
        17-byte XKOP message
    """
    data = bytearray()
    for i in range(4):
        if i < len(records):
            idx, val = records[i]
            if idx is None:
                idx = 0xFF
            if val is None:
                val = 0
            data += bytes([idx & 0xFF, (val >> 8) & 0xFF, val & 0xFF])
        else:
            # Empty slot
            data += b"\xFF\x00\x00"

    # Build complete message
    header = bytes([XKOP_HDR1, XKOP_HDR2, XKOP_TYPE_DATA])
    crc = xkop_crc(header + data)
    return header + data + struct.pack(">H", crc)

def xkop_parse_data(packet: bytes) -> list:
    """
    Parse XKOP data message

    Args:
        packet: 17-byte XKOP message

    Returns:
        List of (index, value) tuples or None if invalid
    """
    if len(packet) != 17:
        print(f"ERROR: Invalid packet length {len(packet)}, expected 17")
        return None

    if packet[0] != XKOP_HDR1 or packet[1] != XKOP_HDR2 or packet[2] != XKOP_TYPE_DATA:
        print(f"ERROR: Invalid header {packet[0]:02X} {packet[1]:02X} {packet[2]:02X}")
        return None

    # Verify CRC
    calc_crc = xkop_crc(packet[:15])
    recv_crc = struct.unpack(">H", packet[15:17])[0]
    if calc_crc != recv_crc:
        print(f"ERROR: CRC mismatch - calculated {calc_crc:04X}, received {recv_crc:04X}")
        return None

    # Parse records
    p = packet[3:15]
    records = []
    for i in range(0, 12, 3):
        idx = p[i]
        val = (p[i+1] << 8) | p[i+2]
        if idx != 0xFF:
            records.append((idx, val))

    return records

def send_xkop_message(host: str, port: int, records: list, verbose: bool = True):
    """Send XKOP message via UDP"""
    message = xkop_build_data(records)

    if verbose:
        print(f"\n=== Sending XKOP Message ===")
        print(f"Target: {host}:{port}")
        print(f"Records: {records}")
        print(f"Message (hex): {message.hex(' ').upper()}")
        print(f"Message (bytes): {len(message)} bytes")

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)

        # Send message
        sock.sendto(message, (host, port))
        print(f"✓ Message sent successfully")

        return sock
    except Exception as e:
        print(f"✗ Send failed: {e}")
        return None

def listen_for_response(sock: socket.socket, timeout: float = 2.0):
    """Listen for XKOP response"""
    print(f"\n=== Listening for Response (timeout: {timeout}s) ===")

    try:
        sock.settimeout(timeout)
        data, addr = sock.recvfrom(2048)

        print(f"✓ Received {len(data)} bytes from {addr[0]}:{addr[1]}")
        print(f"Data (hex): {data.hex(' ').upper()}")

        if len(data) == 17:
            records = xkop_parse_data(data)
            if records is not None:
                print(f"✓ Valid XKOP message")
                print(f"Records: {records}")
                return records
            else:
                print(f"✗ Invalid XKOP message")
        else:
            print(f"✗ Wrong packet size (expected 17 bytes)")

        return None

    except socket.timeout:
        print(f"⧗ No response received (timeout)")
        return None
    except Exception as e:
        print(f"✗ Receive error: {e}")
        return None

def test_connection(host: str, port: int):
    """Test XKOP connection with sample messages"""
    print("="*60)
    print("XKOP UDP Test Client")
    print("="*60)
    print(f"Protocol: UDP")
    print(f"Target: {host}:{port}")
    print(f"Message Format: 17 bytes (CA 35 00 + 12 data + 2 CRC)")
    print("="*60)

    # Test 1: Send a simple message
    print("\n### Test 1: Single Record ###")
    records = [(1, 100)]  # Index 1, Value 100
    sock = send_xkop_message(host, port, records)
    if sock:
        listen_for_response(sock)
        sock.close()

    time.sleep(0.5)

    # Test 2: Send multiple records
    print("\n### Test 2: Multiple Records ###")
    records = [(1, 1), (2, 0), (3, 1), (4, 1)]
    sock = send_xkop_message(host, port, records)
    if sock:
        listen_for_response(sock)
        sock.close()

    time.sleep(0.5)

    # Test 3: Continuous monitoring
    print("\n### Test 3: Listen Mode ###")
    print("Listening for incoming XKOP messages (Ctrl+C to stop)...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 0))  # Bind to random port
        sock.settimeout(10.0)

        local_port = sock.getsockname()[1]
        print(f"Listening on UDP port {local_port}")
        print(f"Waiting for responses from {host}:{port}...")

        while True:
            try:
                data, addr = sock.recvfrom(2048)
                print(f"\n[{time.strftime('%H:%M:%S')}] Received from {addr[0]}:{addr[1]}")
                print(f"Data: {data.hex(' ').upper()}")

                if len(data) == 17:
                    records = xkop_parse_data(data)
                    if records:
                        print(f"Records: {records}")

            except socket.timeout:
                print(".", end="", flush=True)
                continue

    except KeyboardInterrupt:
        print("\n\nStopped by user")
    finally:
        sock.close()

def interactive_mode(host: str, port: int):
    """Interactive mode to send custom messages"""
    print("="*60)
    print("XKOP Interactive Mode")
    print("="*60)
    print(f"Target: {host}:{port}")
    print("\nEnter records as: index,value (e.g., 1,100)")
    print("Multiple records: 1,100 2,200 3,50")
    print("Type 'quit' to exit\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)

    try:
        while True:
            try:
                user_input = input("Records> ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    break

                if not user_input:
                    continue

                # Parse input
                records = []
                for part in user_input.split():
                    try:
                        idx, val = part.split(',')
                        records.append((int(idx), int(val)))
                    except:
                        print(f"Invalid format: {part}")
                        continue

                if records:
                    message = xkop_build_data(records)
                    sock.sendto(message, (host, port))
                    print(f"✓ Sent: {records}")
                    print(f"  Hex: {message.hex(' ').upper()}")

                    # Try to receive response
                    try:
                        data, addr = sock.recvfrom(2048)
                        resp = xkop_parse_data(data)
                        if resp:
                            print(f"✓ Response: {resp}")
                    except socket.timeout:
                        pass

            except KeyboardInterrupt:
                print("\n")
                break
            except Exception as e:
                print(f"Error: {e}")

    finally:
        sock.close()
        print("Goodbye!")

def main():
    parser = argparse.ArgumentParser(
        description='XKOP UDP Test Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test connection
  python xkop_test_client.py --host 10.164.95.201 --port 8001

  # Interactive mode
  python xkop_test_client.py --host 10.164.95.201 --port 8001 --interactive

  # Send custom message
  python xkop_test_client.py --host 10.164.95.201 --port 8001 --send "1,100 2,200"
        """
    )

    parser.add_argument('--host', required=True, help='XKOP server IP address')
    parser.add_argument('--port', type=int, default=8001, help='XKOP server port (default: 8001)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--send', '-s', help='Send custom message (e.g., "1,100 2,200")')

    args = parser.parse_args()

    try:
        if args.interactive:
            interactive_mode(args.host, args.port)
        elif args.send:
            records = []
            for part in args.send.split():
                idx, val = part.split(',')
                records.append((int(idx), int(val)))
            sock = send_xkop_message(args.host, args.port, records)
            if sock:
                listen_for_response(sock)
                sock.close()
        else:
            test_connection(args.host, args.port)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
