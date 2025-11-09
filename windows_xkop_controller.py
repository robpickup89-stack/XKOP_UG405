#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XKOP Controller Simulator for Windows
Simulates a UG405 controller sending DATA messages (Type 0x00) to XKOP client
"""

import socket
import struct
import time
import sys
import threading
from typing import List, Tuple

# ===================== XKOP Protocol =====================
XKOP_HDR1 = 0xCA
XKOP_HDR2 = 0x35
XKOP_TYPE_DATA = 0x00    # Type 0x00: Data message (contains variables)
XKOP_TYPE_STATUS = 0x02  # Type 0x02: Status/Alive message (deprecated, use DATA)

# CRC16 lookup table (matching the C specification)
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

def xkop_crc16_write(data: bytes) -> bytes:
    """
    Calculate CRC16 for XKOP packet
    Returns 2 bytes: [crc1, crc0] matching the C specification
    """
    crc1 = 0
    crc0 = 0

    for byte_val in data:
        temp = (crc1 ^ byte_val) & 0xFF
        crc1 = (crc0 ^ CRC_TABLE[temp]) & 0xFF
        crc0 = (CRC_TABLE[temp] >> 8) & 0xFF

    return bytes([crc1, crc0])

def xkop_crc16_check(data: bytes) -> bool:
    """
    Verify CRC16 for XKOP packet (full 17 bytes including CRC)
    Returns True if CRC is valid
    """
    crc1 = 0
    crc0 = 0

    for byte_val in data:
        temp = (crc1 ^ byte_val) & 0xFF
        crc1 = (crc0 ^ CRC_TABLE[temp]) & 0xFF
        crc0 = (CRC_TABLE[temp] >> 8) & 0xFF

    return (crc1 == 0) and (crc0 == 0)

def xkop_build_data(records: List[Tuple[int, int]]) -> bytes:
    """
    Build an XKOP DATA message (Type 0x00)

    Args:
        records: List of (index, value) tuples, max 4 records
                 index: 0-255, value: 0-65535

    Returns:
        17-byte XKOP packet with correct CRC
    """
    # Build payload (12 bytes = 4 records × 3 bytes each)
    payload = bytearray()
    for i in range(4):
        if i < len(records):
            idx, val = records[i]
            idx = idx & 0xFF  # Ensure 8-bit
            val = val & 0xFFFF  # Ensure 16-bit
            # Format: [index, value_msb, value_lsb]
            payload.append(idx)
            payload.append((val >> 8) & 0xFF)
            payload.append(val & 0xFF)
        else:
            # Empty slot: 0xFF 0x00 0x00
            payload.extend(b"\xFF\x00\x00")

    # Build header (3 bytes) - using DATA type 0x00
    header = bytes([XKOP_HDR1, XKOP_HDR2, XKOP_TYPE_DATA])

    # Calculate CRC on header + payload (15 bytes)
    crc_bytes = xkop_crc16_write(header + payload)

    # Return full packet (17 bytes)
    packet = header + payload + crc_bytes
    return packet

# Legacy alias for backward compatibility
xkop_build_status = xkop_build_data

def parse_xkop_packet(packet: bytes) -> dict:
    """Parse an XKOP packet and return its components"""
    if len(packet) != 17:
        return {"error": f"Invalid length: {len(packet)} (expected 17)"}

    result = {
        "header1": f"0x{packet[0]:02X}",
        "header2": f"0x{packet[1]:02X}",
        "type": f"0x{packet[2]:02X}",
        "records": [],
        "crc": f"0x{packet[15]:02X}{packet[16]:02X}",
        "valid_crc": xkop_crc16_check(packet)
    }

    # Parse 4 records
    for i in range(4):
        offset = 3 + (i * 3)
        idx = packet[offset]
        val = (packet[offset + 1] << 8) | packet[offset + 2]
        if idx != 0xFF:  # Not an empty slot
            result["records"].append({"index": idx, "value": val})

    return result

def print_packet_info(packet: bytes, label: str = "Packet"):
    """Print detailed packet information"""
    hex_str = ' '.join(f'{b:02X}' for b in packet)
    print(f"\n{label}:")
    print(f"  Hex: {hex_str}")
    print(f"  Length: {len(packet)} bytes")

    info = parse_xkop_packet(packet)
    if "error" in info:
        print(f"  Error: {info['error']}")
        return

    print(f"  Header: {info['header1']} {info['header2']}")
    type_name = 'DATA' if packet[2] == XKOP_TYPE_DATA else ('STATUS' if packet[2] == XKOP_TYPE_STATUS else 'UNKNOWN')
    print(f"  Type: {info['type']} ({type_name})")
    print(f"  CRC: {info['crc']} ({'✓ Valid' if info['valid_crc'] else '✗ Invalid'})")
    print(f"  Records ({len(info['records'])}):")
    for rec in info['records']:
        print(f"    - Index {rec['index']:3d}, Value {rec['value']:5d} (0x{rec['value']:04X})")

# ===================== TCP Server =====================
class XKOPController:
    def __init__(self, host='0.0.0.0', port=8001):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.running = False
        self.send_lock = threading.Lock()
        # Internal state for index values (simulates controller memory)
        self.index_values = {}  # Dict[int, int] mapping index (0-255) to value (0-65535)
        self.state_lock = threading.Lock()

    def start(self):
        """Start the TCP server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.running = True
            print(f"\n{'='*60}")
            print(f"XKOP Controller Simulator")
            print(f"{'='*60}")
            print(f"Listening on {self.host}:{self.port}")
            print(f"Waiting for client connection...")
            print(f"{'='*60}\n")

            while self.running:
                try:
                    # Accept connection with timeout
                    self.server_socket.settimeout(1.0)
                    try:
                        client_sock, client_addr = self.server_socket.accept()
                    except socket.timeout:
                        continue

                    self.client_socket = client_sock
                    self.client_address = client_addr
                    print(f"\n✓ Client connected from {client_addr[0]}:{client_addr[1]}")

                    # Handle client in separate thread
                    client_thread = threading.Thread(target=self.handle_client, daemon=True)
                    client_thread.start()
                    client_thread.join()

                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
                        time.sleep(1)

        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()

    def handle_client(self):
        """Handle connected client"""
        try:
            self.client_socket.settimeout(1.0)

            while self.running and self.client_socket:
                try:
                    # Try to receive data from client
                    data = self.client_socket.recv(17)
                    if not data:
                        print(f"\n✗ Client {self.client_address[0]}:{self.client_address[1]} disconnected")
                        break

                    if len(data) == 17:
                        print(f"\nReceived from client {self.client_address[0]}:{self.client_address[1]}:")
                        print_packet_info(data, "  RX Packet")

                        # Parse the packet
                        parsed = parse_xkop_packet(data)
                        if parsed and "records" in parsed and parsed["valid_crc"]:
                            records = parsed["records"]

                            # Determine if this is a READ or WRITE request
                            # WRITE: If any value is non-zero, treat as write operation
                            # READ: If all values are zero, treat as read request
                            is_write = any(rec["value"] != 0 for rec in records)

                            if is_write:
                                # WRITE MODE: Store the values sent by client
                                print(f"  WRITE request:")
                                with self.state_lock:
                                    for rec in records:
                                        idx = rec["index"]
                                        val = rec["value"]
                                        self.index_values[idx] = val
                                        print(f"    Index {idx} ← {val} (0x{val:04X})")

                                # Send acknowledgment with same values
                                response_records = [(rec["index"], rec["value"]) for rec in records]
                                response_packet = xkop_build_data(response_records)
                                self.client_socket.sendall(response_packet)
                                print(f"\n  Sent ACK to client:")
                                print_packet_info(response_packet, "    ACK Packet")

                            else:
                                # READ MODE: Client sends indices with value 0, wants current values
                                requested_indices = [rec["index"] for rec in records]
                                print(f"  READ request for indices: {requested_indices}")

                                # Build response with current values for requested indices
                                response_records = []
                                with self.state_lock:
                                    for idx in requested_indices[:4]:  # Max 4 indices
                                        value = self.index_values.get(idx, 0)  # Default to 0 if not set
                                        response_records.append((idx, value))

                                # Send response packet
                                if response_records:
                                    response_packet = xkop_build_data(response_records)
                                    self.client_socket.sendall(response_packet)
                                    print(f"\n  Sent response to client:")
                                    print_packet_info(response_packet, "    Response Packet")

                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Receive error: {e}")
                    break

        except Exception as e:
            print(f"Client handler error: {e}")
        finally:
            try:
                if self.client_socket:
                    self.client_socket.close()
            except:
                pass
            self.client_socket = None
            self.client_address = None

    def send_data(self, records: List[Tuple[int, int]]):
        """Send DATA message to connected client"""
        with self.send_lock:
            if not self.client_socket:
                print("✗ No client connected, cannot send")
                return False

            try:
                packet = xkop_build_data(records)
                self.client_socket.sendall(packet)

                print(f"\nSent to client {self.client_address[0]}:{self.client_address[1]}:")
                print_packet_info(packet, "  TX Packet")
                return True

            except Exception as e:
                print(f"✗ Send error: {e}")
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
                return False

    # Legacy alias for backward compatibility
    send_status = send_data

    def set_index_value(self, index: int, value: int):
        """Set the value for a specific index"""
        if 0 <= index <= 255 and 0 <= value <= 65535:
            with self.state_lock:
                self.index_values[index] = value
            print(f"✓ Set index {index} = {value} (0x{value:04X})")
            return True
        else:
            print(f"✗ Invalid index ({index}) or value ({value})")
            return False

    def get_index_value(self, index: int) -> int:
        """Get the value for a specific index"""
        with self.state_lock:
            return self.index_values.get(index, 0)

    def list_index_values(self):
        """List all set index values"""
        with self.state_lock:
            if not self.index_values:
                print("No index values set")
                return

            print(f"\nCurrent Index Values ({len(self.index_values)}):")
            for idx in sorted(self.index_values.keys()):
                val = self.index_values[idx]
                print(f"  Index {idx:3d}: {val:5d} (0x{val:04X})")

    def stop(self):
        """Stop the server"""
        self.running = False
        try:
            if self.client_socket:
                self.client_socket.close()
        except:
            pass
        try:
            if self.server_socket:
                self.server_socket.close()
        except:
            pass

# ===================== Test Scenarios =====================
def test_crc():
    """Test CRC calculation matches expected values"""
    print("\n" + "="*60)
    print("CRC16 TEST")
    print("="*60)

    # Your example packet
    test_records = [
        (0, 1),   # Index 0, Value 1
        (1, 0),   # Index 1, Value 0
        (3, 1),   # Index 3, Value 1
        (4, 0),   # Index 4, Value 0
    ]

    packet = xkop_build_data(test_records)
    print_packet_info(packet, "Test Packet")

    # Verify CRC
    is_valid = xkop_crc16_check(packet)
    print(f"\nCRC Verification: {'✓ PASS' if is_valid else '✗ FAIL'}")

def interactive_mode(controller: XKOPController):
    """Interactive mode for sending custom packets"""
    print("\n" + "="*60)
    print("INTERACTIVE MODE (Read/Write Enabled)")
    print("="*60)
    print("Commands:")
    print("  s <idx1> <val1> [idx2 val2] ... - Send data message (max 4 records)")
    print("  p <scenario>                    - Send predefined scenario")
    print("  i <idx> <val>                   - Set index value (for read responses)")
    print("  l                               - List all index values")
    print("  g <idx>                         - Get value for specific index")
    print("  t                               - Run CRC test")
    print("  q                               - Quit")
    print("="*60)
    print("READ/WRITE PROTOCOL:")
    print("  WRITE: Client sends indices with NON-ZERO values")
    print("         → Controller stores values and sends ACK")
    print("  READ:  Client sends indices with ZERO values")
    print("         → Controller responds with current values")
    print("="*60 + "\n")

    # Predefined scenarios
    scenarios = {
        '1': ([(0, 1), (1, 0), (3, 1), (4, 0)], "Your example packet"),
        '2': ([(0, 100), (1, 200), (2, 300), (3, 400)], "All indices 0-3, values 100-400"),
        '3': ([(0, 1)], "Single record: Index 0, Value 1"),
        '4': ([(0, 0), (1, 0), (2, 0), (3, 0)], "All zeros"),
        '5': ([(10, 500), (20, 1000)], "Index 10=500, Index 20=1000"),
    }

    while True:
        try:
            cmd = input("\nCommand> ").strip()
            if not cmd:
                continue

            parts = cmd.split()
            command = parts[0].lower()

            if command == 'q':
                break

            elif command == 't':
                test_crc()

            elif command == 'i':
                if len(parts) < 3:
                    print("Usage: i <index> <value>")
                    print("Example: i 0 100")
                    continue

                try:
                    idx = int(parts[1])
                    val = int(parts[2])
                    controller.set_index_value(idx, val)
                except ValueError:
                    print(f"Invalid number: {parts[1]} or {parts[2]}")

            elif command == 'l':
                controller.list_index_values()

            elif command == 'g':
                if len(parts) < 2:
                    print("Usage: g <index>")
                    print("Example: g 0")
                    continue

                try:
                    idx = int(parts[1])
                    val = controller.get_index_value(idx)
                    print(f"Index {idx}: {val} (0x{val:04X})")
                except ValueError:
                    print(f"Invalid index: {parts[1]}")

            elif command == 'p':
                if len(parts) < 2:
                    print("Available scenarios:")
                    for key, (records, desc) in scenarios.items():
                        print(f"  {key}: {desc}")
                    continue

                scenario_key = parts[1]
                if scenario_key in scenarios:
                    records, desc = scenarios[scenario_key]
                    print(f"Sending scenario {scenario_key}: {desc}")
                    controller.send_data(records)
                else:
                    print(f"Unknown scenario: {scenario_key}")

            elif command == 's':
                if len(parts) < 3 or len(parts) % 2 == 0:
                    print("Usage: s <idx1> <val1> [idx2 val2] [idx3 val3] [idx4 val4]")
                    print("Example: s 0 1 1 0 3 1 4 0")
                    continue

                records = []
                for i in range(1, len(parts), 2):
                    try:
                        idx = int(parts[i])
                        val = int(parts[i+1])
                        if idx < 0 or idx > 255:
                            print(f"Warning: Index {idx} out of range (0-255)")
                        if val < 0 or val > 65535:
                            print(f"Warning: Value {val} out of range (0-65535)")
                        records.append((idx, val))
                    except ValueError:
                        print(f"Invalid number: {parts[i]} or {parts[i+1]}")
                        break

                if records:
                    if len(records) > 4:
                        print(f"Warning: Only first 4 records will be sent (you provided {len(records)})")
                        records = records[:4]
                    controller.send_data(records)

            else:
                print(f"Unknown command: {command}")

        except KeyboardInterrupt:
            print("\nInterrupted")
            break
        except Exception as e:
            print(f"Error: {e}")

def auto_send_mode(controller: XKOPController, interval=2.0):
    """Automatically send periodic data messages"""
    print(f"\nAuto-send mode: sending data messages every {interval} seconds")
    print("Press Ctrl+C to stop\n")

    # Cycling through different values
    cycle = 0
    try:
        while True:
            # Create cycling pattern
            records = [
                (0, (cycle + 0) % 2),  # Index 0: alternates 0,1
                (1, (cycle + 1) % 2),  # Index 1: alternates 1,0
                (2, cycle % 256),      # Index 2: counter
                (3, (cycle * 10) % 65536),  # Index 3: larger counter
            ]

            controller.send_data(records)
            cycle += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nAuto-send stopped")

# ===================== Main =====================
def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--test-crc':
        test_crc()
        return

    # Create controller
    controller = XKOPController(host='0.0.0.0', port=8001)

    # Start server in background thread
    server_thread = threading.Thread(target=controller.start, daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(0.5)

    # Choose mode
    print("\nSelect mode:")
    print("  1 - Interactive mode (manual control)")
    print("  2 - Auto-send mode (periodic updates)")
    print("  3 - CRC test only")

    try:
        choice = input("\nMode (1-3)> ").strip()

        if choice == '1':
            interactive_mode(controller)
        elif choice == '2':
            interval_str = input("Send interval in seconds (default 2.0)> ").strip()
            interval = float(interval_str) if interval_str else 2.0
            auto_send_mode(controller, interval)
        elif choice == '3':
            test_crc()
        else:
            print("Invalid choice, using interactive mode")
            interactive_mode(controller)

    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        controller.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()
