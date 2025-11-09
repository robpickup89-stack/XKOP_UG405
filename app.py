#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XKOP Tool - CLIENT MODE
Client connects to controller using XKOPMV protocol (UDP)
- Listens for data packets from controller (updates outputs)
- Sends data packets to controller when SNMP SET is received (sends inputs)
- PreIndex: 1 for ALL inputs, 0 for ALL outputs
"""

import os, sys, socket, struct, threading, time, datetime, urllib.request, json
from typing import Dict, List, Tuple, Optional, Literal, TypedDict
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=None)

# ===================== Port Availability Checker =====================
def find_available_port(preferred_port: int, max_attempts: int = 10, check_both_protocols: bool = False) -> int:
    """
    Find an available port, starting with the preferred port.
    If preferred port is in use, try subsequent ports.

    Args:
        preferred_port: The port to try first
        max_attempts: How many sequential ports to check
        check_both_protocols: If True, check both UDP and TCP availability
    """
    for offset in range(max_attempts):
        port = preferred_port + offset
        tcp_available = False
        udp_available = False

        # Check TCP port availability
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(('0.0.0.0', port))
            test_sock.close()
            tcp_available = True
        except OSError:
            pass

        # Check UDP port availability if needed
        if check_both_protocols:
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.bind(('0.0.0.0', port))
                test_sock.close()
                udp_available = True
            except OSError:
                pass

            # Both must be available
            if tcp_available and udp_available:
                return port
        else:
            # Only TCP needs to be available
            if tcp_available:
                return port

    # If all attempts failed, return the preferred port (will fail with clear error)
    return preferred_port

# ===================== Logs =====================
STATE_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
XKOP_LOG: List[str] = []
SNMP_LOG: List[str] = []
APP_LOG:  List[str] = []

def _log(buf: List[str], msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    with LOG_LOCK:
        buf.append(line)
        if len(buf) > 5000:
            del buf[:2000]
    print(line, flush=True)

def log_app(m):  _log(APP_LOG,  m)
def log_snmp(m): _log(SNMP_LOG, m)
def log_xkop(m): _log(XKOP_LOG, m)

# ===================== Config & State =====================
CONFIG = {
    "ip": "",
    "instation_ip": "127.0.0.1",
    "xkop": 1,
    "snmp_port": 161,
    "rows": []
}

class Row(TypedDict, total=False):
    nr: str; input: str; in_scn: str; in_func: str; in_idx: str; in_value: Optional[int]
    output: str; out_scn: str; out_func: str; out_idx: str; out_value: Optional[int]

STATE = {"rows": [], "by_key": {}, "last_update": time.time()}
TEST_MODE = False
TEST_MODE_EXPIRY: Optional[datetime.datetime] = None

def seed_rows_from_config_locked():
    rows: List[Row] = []
    for r in CONFIG.get("rows", []):
        rows.append({
            "nr": r.get("nr",""), "input": r.get("input",""),
            "in_scn": r.get("in_scn",""), "in_func": r.get("in_func","-"), "in_idx": r.get("in_idx",""), "in_value": None,
            "output": r.get("output",""), "out_scn": r.get("out_scn",""), "out_func": r.get("out_func","-"), 
            "out_idx": r.get("out_idx",""), "out_value": None,
        })
    STATE["rows"] = rows
    STATE["by_key"] = {(row["nr"] or row["input"] or str(i+1)): row for i,row in enumerate(rows)}
    STATE["last_update"] = time.time()
    log_app(f"Seeded {len(rows)} rows from config")

def update_in_value(key: str, value):
    with STATE_LOCK:
        row = STATE["by_key"].get(key)
        if row is not None:
            row["in_value"] = int(value) if value is not None else None
            STATE["last_update"] = time.time()

def update_out_value(key: str, value):
    with STATE_LOCK:
        row = STATE["by_key"].get(key)
        if row is not None:
            row["out_value"] = int(value) if value is not None else None
            STATE["last_update"] = time.time()

# ===================== XKOP =====================
XKOP_HDR1, XKOP_HDR2 = 0xCA, 0x35
XKOP_TYPE_DATA = 0x00    # Type 0: Data message (contains variables)
XKOP_TYPE_TIME = 0x01    # Type 1: Time message
XKOP_TYPE_ALIVE = 0x02   # Type 2: Alive message (keep-alive, no data)
XKOP_LISTEN_ADDR = ("0.0.0.0", 8001)
XKOP_TX_ADDR     = ("127.0.0.1", 8001)
xkop_listener_sock: Optional[socket.socket] = None
xkop_tcp_listener_sock: Optional[socket.socket] = None

CRC_TABLE = [
    0x0000,0x0f89,0x1f12,0x109b,0x3e24,0x31ad,0x2136,0x2ebf,0x7c48,0x73c1,0x635a,0x6cd3,0x426c,0x4de5,0x5d7e,0x52f7,
    0xf081,0xff08,0xef93,0xe01a,0xcea5,0xc12c,0xd1b7,0xde3e,0x8cc9,0x8340,0x93db,0x9c52,0xb2ed,0xbd64,0xadff,0xa276,
    0xe102,0xee8b,0xfe10,0xf199,0xdf26,0xd0af,0xc034,0xcfbd,0x9d4a,0x92c3,0x8258,0x8dd1,0xa36e,0xace7,0xbc7c,0xb3f5,
    0x1183,0x1e0a,0x0e91,0x0118,0x2fa7,0x202e,0x30b5,0x3f3c,0x6dcb,0x6242,0x72d9,0x7d50,0x53ef,0x5c66,0x4cfd,0x4374,
    0xc204,0xcd8d,0xdd16,0xd29f,0xfc20,0xf3a9,0xe332,0xecbb,0xbe4c,0xb1c5,0xa15e,0xaed7,0x8068,0x8fe1,0x9f7a,0x90f3,
    0x3285,0x3d0c,0x2d97,0x221e,0x0ca1,0x0328,0x13b3,0x1c3a,0x4ecd,0x4144,0x51df,0x5e56,0x70e9,0x7f60,0x6ffb,0x6072,
    0x2306,0x2c8f,0x3c14,0x339d,0x1d22,0x12ab,0x0230,0x0db9,0x5f4e,0x50c7,0x405c,0x4fd5,0x616a,0x6ee3,0x7e78,0x71f1,
    0xd387,0xdc0e,0xcc95,0xc31c,0xeda3,0xe22a,0xf2b1,0xfd38,0xafcf,0xa046,0xb0dd,0xbf54,0x91eb,0x9e62,0x8ef9,0x8170,
    0x8408,0x8b81,0x9b1a,0x9493,0xba2c,0xb5a5,0xa53e,0xaab7,0xf840,0xf7c9,0xe752,0xe8db,0xc664,0xc9ed,0xd976,0xd6ff,
    0x7489,0x7b00,0x6b9b,0x6412,0x4aad,0x4524,0x55bf,0x5a36,0x08c1,0x0748,0x17d3,0x185a,0x36e5,0x396c,0x29f7,0x267e,
    0x650a,0x6a83,0x7a18,0x7591,0x5b2e,0x54a7,0x443c,0x4bb5,0x1942,0x16cb,0x0650,0x09d9,0x2766,0x28ef,0x3874,0x37fd,
    0x958b,0x9a02,0x8a99,0x8510,0xabaf,0xa426,0xb4bd,0xbb34,0xe9c3,0xe64a,0xf6d1,0xf958,0xd7e7,0xd86e,0xc8f5,0xc77c,
    0xa70e,0xa887,0xb81c,0xb795,0x992a,0x96a3,0x8638,0x89b1,0xdb46,0xd4cf,0xc454,0xcbdd,0xe562,0xeaeb,0xfa70,0xf5f9,
    0x578f,0x5806,0x489d,0x4714,0x69ab,0x6622,0x76b9,0x7930,0x2bc7,0x244e,0x34d5,0x3b5c,0x15e3,0x1a6a,0x0af1,0x0578,
]

def xkop_crc(data: bytes) -> int:
    crc = 0
    for b in data:
        t = CRC_TABLE[(crc ^ b) & 0xFF]
        crc = ((crc >> 8) ^ t) & 0xFFFF
    return crc

def xkop_build_data(records: List[Tuple[int,int]]) -> bytes:
    data = bytearray()
    for i in range(4):
        if i < len(records):
            idx, val = records[i]
            if idx is None: idx = 0xFF
            if val is None: val = 0
            data += bytes([idx & 0xFF, (val >> 8) & 0xFF, val & 0xFF])
        else:
            data += b"\xFF\x00\x00"
    header = bytes([XKOP_HDR1, XKOP_HDR2, XKOP_TYPE_DATA])
    crc = xkop_crc(header + data)
    return header + data + struct.pack(">H", crc)

def xkop_parse_data(packet: bytes) -> Optional[List[Tuple[int,int]]]:
    """Parse XKOP packet and return list of (index, value) tuples.

    Returns:
        - List of (index, value) tuples for data messages (type 0x00)
        - Empty list for alive messages (type 0x02)
        - None for invalid packets
    """
    # Check packet length and headers
    if len(packet) != 17:
        log_xkop(f"  Parse fail: wrong length {len(packet)}, expected 17")
        return None
    if packet[0] != XKOP_HDR1:
        log_xkop(f"  Parse fail: wrong HDR1 0x{packet[0]:02X}, expected 0x{XKOP_HDR1:02X}")
        return None
    if packet[1] != XKOP_HDR2:
        log_xkop(f"  Parse fail: wrong HDR2 0x{packet[1]:02X}, expected 0x{XKOP_HDR2:02X}")
        return None

    # Get message type
    msg_type = packet[2]

    # Accept data (0x00) and alive (0x02) messages
    if msg_type not in (XKOP_TYPE_DATA, XKOP_TYPE_ALIVE):
        log_xkop(f"  Parse fail: unknown TYPE 0x{msg_type:02X}, expected 0x{XKOP_TYPE_DATA:02X} or 0x{XKOP_TYPE_ALIVE:02X}")
        return None

    # Check CRC
    calc = xkop_crc(packet[:15])
    recv = struct.unpack(">H", packet[15:17])[0]
    if calc != recv:
        log_xkop(f"  Parse fail: CRC mismatch calc=0x{calc:04X} recv=0x{recv:04X}")
        return None

    # Alive messages (type 0x02) have no data records - just return empty list
    if msg_type == XKOP_TYPE_ALIVE:
        log_xkop(f"  Received alive message (keep-alive)")
        return []

    # Extract records from data messages (type 0x00)
    p = packet[3:15]
    if len(p) != 12:
        log_xkop(f"  Parse fail: payload length {len(p)}, expected 12")
        return None

    recs = []
    for i in range(0, 12, 3):
        idx = p[i]
        val = (p[i+1] << 8) | p[i+2]
        if idx != 0xFF:
            recs.append((idx, val))
    return recs

def udp_send(data: bytes, target: Tuple[str,int]):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.sendto(data, target)
        log_xkop(f"UDP TX to {target}: {len(data)} bytes")
    except Exception as e:
        log_xkop(f"UDP TX FAILED to {target}: {e}")
    finally: s.close()

def tcp_send(data: bytes):
    """Send XKOP data to controller via TCP"""
    global xkop_tcp_listener_sock
    if not xkop_tcp_listener_sock:
        log_xkop(f"TCP TX FAILED: not connected to controller")
        return
    try:
        xkop_tcp_listener_sock.sendall(data)
        log_xkop(f"TCP TX to controller: {len(data)} bytes")
    except Exception as e:
        log_xkop(f"TCP TX FAILED: {e}")
        # Close socket on send failure to trigger reconnect
        try:
            xkop_tcp_listener_sock.close()
        except:
            pass
        xkop_tcp_listener_sock = None

def xkop_listener():
    """Receive XKOP from controller, update output values"""
    global xkop_listener_sock
    while True:
        try:
            sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(XKOP_LISTEN_ADDR); sock.settimeout(1.0)
            xkop_listener_sock=sock
            log_xkop(f"Listening UDP {XKOP_LISTEN_ADDR[0]}:{XKOP_LISTEN_ADDR[1]}")
            while True:
                try: data,addr=sock.recvfrom(2048)
                except socket.timeout: continue
                except OSError: break
                if not data or len(data)!=17: continue
                recs=xkop_parse_data(data)
                if recs is None: continue
                log_xkop(f"RX from {addr}: {recs}")

                with STATE_LOCK:
                    rows = STATE["rows"][:]

                for (idx,val) in recs:
                    for r in rows:
                        try:
                            out_idx_raw = r.get("out_idx", "")
                            if not out_idx_raw:
                                continue
                            # Handle comma-separated indices, take first one
                            out_idx_parts = str(out_idx_raw).split(",")
                            if not out_idx_parts or not out_idx_parts[0].strip():
                                continue
                            ridx = int(out_idx_parts[0].strip())
                            # Validate index is in valid range (0-255)
                            if ridx < 0 or ridx > 255:
                                continue
                        except (ValueError, IndexError, AttributeError) as e:
                            log_xkop(f"  Error parsing out_idx for row {r.get('nr','')}: {e}")
                            continue

                        if ridx == idx:
                            key = r.get("nr") or r.get("output") or ""
                            update_out_value(key, val)
                            log_xkop(f"  Updated output row {r.get('nr','')} (idx={idx}) = {val}")

        except Exception as e:
            log_xkop(f"ERR {e}")
        finally:
            try:
                if xkop_listener_sock: xkop_listener_sock.close()
            except: pass
            time.sleep(1.0)

def xkop_tcp_listener():
    """Connect to controller as TCP client for bidirectional XKOP communication"""
    global xkop_tcp_listener_sock
    while True:
        try:
            # Get controller address
            controller_ip = XKOP_TX_ADDR[0]
            controller_port = XKOP_TX_ADDR[1]

            if not controller_ip or controller_ip == "127.0.0.1":
                log_xkop(f"TCP waiting for controller IP to be set...")
                time.sleep(5.0)
                continue

            # Connect to controller
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(5.0)  # 5 second timeout for connect

            log_xkop(f"TCP connecting to controller {controller_ip}:{controller_port}...")
            sock.connect((controller_ip, controller_port))
            log_xkop(f"TCP connected to controller {controller_ip}:{controller_port}")

            xkop_tcp_listener_sock = sock
            sock.settimeout(1.0)  # 1 second timeout for recv (to check for reconnect)

            # Receive loop
            while True:
                try:
                    # Read exactly 17 bytes for XKOP message
                    data = b''
                    while len(data) < 17:
                        chunk = sock.recv(17 - len(data))
                        if not chunk:
                            # Connection closed by controller
                            log_xkop(f"TCP controller {controller_ip}:{controller_port} disconnected")
                            break
                        data += chunk

                    if len(data) != 17:
                        break

                    # Parse XKOP message
                    recs = xkop_parse_data(data)
                    if recs is None:
                        hex_data = ' '.join(f'{b:02X}' for b in data)
                        log_xkop(f"TCP invalid XKOP from controller, received: {hex_data}")
                        continue

                    log_xkop(f"TCP RX from controller: {recs}")

                    # Update output values
                    with STATE_LOCK:
                        rows = STATE["rows"][:]

                    for (idx, val) in recs:
                        for r in rows:
                            try:
                                out_idx_raw = r.get("out_idx", "")
                                if not out_idx_raw:
                                    continue
                                # Handle comma-separated indices, take first one
                                out_idx_parts = str(out_idx_raw).split(",")
                                if not out_idx_parts or not out_idx_parts[0].strip():
                                    continue
                                ridx = int(out_idx_parts[0].strip())
                                # Validate index is in valid range (0-255)
                                if ridx < 0 or ridx > 255:
                                    continue
                            except (ValueError, IndexError, AttributeError) as e:
                                log_xkop(f"  Error parsing out_idx for row {r.get('nr','')}: {e}")
                                continue

                            if ridx == idx:
                                key = r.get("nr") or r.get("output") or ""
                                update_out_value(key, val)
                                log_xkop(f"  TCP Updated output row {r.get('nr','')} (idx={idx}) = {val}")

                except socket.timeout:
                    # Timeout is normal, just continue
                    continue
                except Exception as e:
                    log_xkop(f"TCP receive error: {e}")
                    break

        except ConnectionRefusedError:
            log_xkop(f"TCP connection refused by {XKOP_TX_ADDR[0]}:{XKOP_TX_ADDR[1]}")
            time.sleep(5.0)
        except socket.timeout:
            log_xkop(f"TCP connection timeout to {XKOP_TX_ADDR[0]}:{XKOP_TX_ADDR[1]}")
            time.sleep(5.0)
        except Exception as e:
            log_xkop(f"TCP client ERR {e}")
            time.sleep(5.0)
        finally:
            try:
                if xkop_tcp_listener_sock:
                    xkop_tcp_listener_sock.close()
                    xkop_tcp_listener_sock = None
            except:
                pass

# ===================== UTMC OID Functions =====================
CONTROL_FUNCS: Dict[str, Tuple[str, str]] = {
    "DX": ("4.2.1.3",  "scalar"), "Dn": ("4.2.1.4",  "bitmask"), "Fn": ("4.2.1.5",  "bitmask"),
    "SFn":("4.2.1.6",  "bitmask"), "PV": ("4.2.1.7",  "scalar"), "PX": ("4.2.1.8",  "scalar"),
    "SO": ("4.2.1.9",  "scalar"), "SG": ("4.2.1.10", "scalar"), "LO": ("4.2.1.11", "scalar"),
    "LL": ("4.2.1.12", "scalar"), "TS": ("4.2.1.13", "scalar"), "FM": ("4.2.1.14", "scalar"),
    "TO": ("4.2.1.15", "scalar"), "HI": ("4.2.1.16", "scalar"), "CP": ("4.2.1.17", "scalar"),
    "EP": ("4.2.1.18", "scalar"), "GO": ("4.2.1.19", "scalar"), "FF": ("4.2.1.20", "scalar"),
    "MO": ("4.2.1.21", "scalar"),
}

REPLY_FUNCS: Dict[str, Tuple[str, str]] = {
    "Gn":  ("5.1.1.3",  "bitmask"), "GX":  ("5.1.1.4",  "scalar"), "DF":  ("5.1.1.5",  "scalar"),
    "FC":  ("5.1.1.6",  "scalar"), "SCn": ("5.1.1.7",  "bitmask"), "HC":  ("5.1.1.8",  "scalar"),
    "WI":  ("5.1.1.9",  "scalar"), "PC":  ("5.1.1.10", "scalar"), "PR":  ("5.1.1.11", "scalar"),
    "CG":  ("5.1.1.12", "scalar"), "GR1": ("5.1.1.13", "scalar"), "SDn": ("5.1.1.14", "bitmask"),
    "MC":  ("5.1.1.15", "scalar"), "CF":  ("5.1.1.16", "scalar"), "LE":  ("5.1.1.17", "scalar"),
    "RR":  ("5.1.1.18", "scalar"), "LFn": ("5.1.1.19", "bitmask"), "RF1": ("5.1.1.20", "scalar"),
    "RF2": ("5.1.1.21", "scalar"), "EV":  ("5.1.1.22", "scalar"), "VC":  ("5.1.1.23", "scalar"),
    "VO":  ("5.1.1.24", "scalar"), "GPn": ("5.1.1.25", "bitmask"), "VQ":  ("5.1.1.26", "scalar"),
    "CA":  ("5.1.1.27", "scalar"), "CR":  ("5.1.1.28", "scalar"), "CL":  ("5.1.1.29", "scalar"),
    "CSn": ("5.1.1.30", "bitmask"), "TF":  ("5.1.1.31", "scalar"), "VSn": ("5.1.1.32", "bitmask"),
    "CO":  ("5.1.1.33", "scalar"), "EC":  ("5.1.1.34", "scalar"), "CS":  ("5.1.1.35", "scalar"),
    "FR":  ("5.1.1.36", "scalar"), "BDn": ("5.1.1.37", "bitmask"), "TPn": ("5.1.1.38", "bitmask"),
    "SB":  ("5.1.1.39", "scalar"), "LC":  ("5.1.1.40", "scalar"), "MR":  ("5.1.1.41", "scalar"),
    "MF":  ("5.1.1.42", "scalar"), "ML":  ("5.1.1.43", "scalar"),
}

def parse_utmc_oid(oid_str: str) -> Optional[Tuple[str,str,int,str]]:
    try:
        parts = [int(x) for x in oid_str.strip('.').split('.')]
    except:
        return None
    base = [1,3,6,1,4,1,13267,3,2]
    if parts[:len(base)] != base:
        return None
    rest = parts[len(base):]
    if len(rest) < 5:
        return None
    path = '.'.join(map(str, rest[:4]))
    preIndex = rest[4]
    scn = ''
    if len(rest) >= 6:
        scn_len = rest[5]
        scn_digits = rest[6:6+scn_len]
        try:
            scn = ''.join(chr(d) for d in scn_digits)
        except:
            scn = ''
    direction = 'in' if path.startswith('4.') else 'out'
    table = CONTROL_FUNCS if direction == 'in' else REPLY_FUNCS
    func = None
    for f, (p, _) in table.items():
        if p == path:
            func = f
            break
    if not func:
        func = f"UNK({path})"
    return (direction, func, preIndex, scn)

def rows_matching(direction: str, func: str, scn: str) -> List[Row]:
    with STATE_LOCK:
        rows = STATE["rows"][:]
    field_prefix = direction
    result = []
    for r in rows:
        r_func = (r.get(f"{field_prefix}_func") or "").strip()
        r_scn = (r.get(f"{field_prefix}_scn") or "").strip()
        if r_func == "-" or not r_func:
            continue
        if r_func == func and r_scn == scn:
            result.append(r)
    return result

# ===================== SNMP Endpoints =====================
@app.get("/snmp/get")
def snmp_get():
    oid = request.args.get("oid", "")
    parsed = parse_utmc_oid(oid)
    if not parsed:
        return jsonify({"oid": oid, "value": 0, "type": "integer"})
    direction, func, preIndex, scn = parsed
    if direction != 'out':
        return jsonify({"oid": oid, "value": 0, "type": "integer"})
    # ✅ Outputs accept both preIndex 0 and 1
    if preIndex not in (0, 1):
        return jsonify({"oid": oid, "value": 0, "type": "integer"})
    func_info = REPLY_FUNCS.get(func)
    if not func_info:
        return jsonify({"oid": oid, "value": 0, "type": "integer"})
    _, kind = func_info
    rows = rows_matching('out', func, scn)
    if not rows:
        return jsonify({"oid": oid, "value": 0, "type": "integer"})
    if kind == "bitmask":
        mask = 0
        for r in rows:
            try:
                out_idx_raw = r.get("out_idx", "")
                if not out_idx_raw:
                    continue
                # Handle comma-separated indices, take first one
                out_idx_parts = str(out_idx_raw).split(",")
                if not out_idx_parts or not out_idx_parts[0].strip():
                    continue
                idx = int(out_idx_parts[0].strip())
                # Validate index is in valid range (0-255)
                if idx < 0 or idx > 255:
                    continue
                bit = max(0, idx - 1)
                val = r.get("out_value") or 0
                if val:
                    mask |= (1 << bit)
            except (ValueError, IndexError, AttributeError):
                continue
        log_snmp(f"GET {oid} = {mask}")
        return jsonify({"oid": oid, "value": str(mask), "type": "string"})
    else:
        if rows:
            val = rows[0].get("out_value") or 0
            log_snmp(f"GET {oid} = {val}")
            return jsonify({"oid": oid, "value": val, "type": "integer"})
        return jsonify({"oid": oid, "value": 0, "type": "integer"})

@app.post("/snmp/set")
def snmp_set():
    data = request.get_json(force=True) or {}
    oid = data.get("oid", "")
    value = int(data.get("value", 0))
    parsed = parse_utmc_oid(oid)
    if not parsed:
        return jsonify({"ok": False, "error": "not UTMC OID"})
    direction, func, preIndex, scn = parsed
    if direction != 'in':
        return jsonify({"ok": False, "error": "wrong direction"})
    # ✅ ALL inputs must have preIndex = 1
    if preIndex != 1:
        log_snmp(f"SET {oid} = {value} IGNORED (inputs require preIndex=1)")
        return jsonify({"ok": False, "error": "invalid preIndex"})
    func_info = CONTROL_FUNCS.get(func)
    if not func_info:
        return jsonify({"ok": False, "error": "unknown function"})
    _, kind = func_info
    rows = rows_matching('in', func, scn)
    if not rows:
        return jsonify({"ok": False, "error": "not configured"})

    log_snmp(f"SET {oid} ({func} SCN={scn}) = {value} → {len(rows)} rows")

    if kind == "bitmask":
        xkop_records = []

        for r in rows:
            try:
                in_idx_raw = r.get("in_idx", "")
                if not in_idx_raw:
                    continue
                # Handle comma-separated indices, take first one
                in_idx_parts = str(in_idx_raw).split(",")
                if not in_idx_parts or not in_idx_parts[0].strip():
                    continue
                idx = int(in_idx_parts[0].strip())
                # Validate index is in valid range (0-255)
                if idx < 0 or idx > 255:
                    log_snmp(f"  Row {r.get('nr','')} has invalid index {idx} (must be 0-255)")
                    continue

                bit = max(0, idx - 1)
                bit_val = 1 if (value & (1 << bit)) else 0

                key = r.get("nr") or r.get("input") or ""
                if key:
                    update_in_value(key, bit_val)
                    log_snmp(f"  Row {r.get('nr','')} idx={idx} bit={bit} val={bit_val}")

                xkop_records.append((idx, bit_val))
            except (ValueError, IndexError, AttributeError) as e:
                log_snmp(f"  Error parsing in_idx for row {r.get('nr','')}: {e}")
                continue

        if xkop_records and not TEST_MODE:
            for i in range(0, len(xkop_records), 4):
                batch = xkop_records[i:i+4]
                pkt = xkop_build_data(batch)
                udp_send(pkt, XKOP_TX_ADDR)
                tcp_send(pkt)
                log_xkop(f"TX bitmask {func}: {batch}")

    else:
        # Scalar - just use first matching row
        if rows:
            r = rows[0]
            try:
                in_idx_raw = r.get("in_idx", "")
                if not in_idx_raw:
                    log_snmp(f"  Row {r.get('nr','')} has no in_idx configured")
                    return jsonify({"ok": False, "error": "no index configured"})
                # Handle comma-separated indices, take first one
                in_idx_parts = str(in_idx_raw).split(",")
                if not in_idx_parts or not in_idx_parts[0].strip():
                    log_snmp(f"  Row {r.get('nr','')} has empty in_idx")
                    return jsonify({"ok": False, "error": "empty index"})
                idx = int(in_idx_parts[0].strip())
                # Validate index is in valid range (0-255)
                if idx < 0 or idx > 255:
                    log_snmp(f"  Row {r.get('nr','')} has invalid index {idx} (must be 0-255)")
                    return jsonify({"ok": False, "error": "invalid index range"})

                key = r.get("nr") or r.get("input") or ""
                if key:
                    update_in_value(key, value)
                    log_snmp(f"  Row {r.get('nr','')} idx={idx} val={value}")

                if not TEST_MODE:
                    pkt = xkop_build_data([(idx, value)])
                    udp_send(pkt, XKOP_TX_ADDR)
                    tcp_send(pkt)
                    log_xkop(f"TX scalar {func}: idx={idx}, val={value}")
            except (ValueError, IndexError, AttributeError) as e:
                log_snmp(f"  Error parsing in_idx for row {r.get('nr','')}: {e}")
                return jsonify({"ok": False, "error": str(e)})

    return jsonify({"ok": True, "oid": oid, "value": value})

# ===================== HTTP Endpoints with Full Web UI =====================
@app.get("/")
def index():
    try:
        return send_from_directory(os.path.dirname(__file__), "xkop.html")
    except:
        return """<!DOCTYPE html><html><body>
        <h1>XKOP Tool - CLIENT MODE</h1>
        <p><strong>Missing xkop.html file!</strong></p>
        <p>Place xkop.html in the same directory as app.py</p>
        <p>API endpoints still work:</p>
        <ul>
        <li><a href="/config">GET /config</a></li>
        <li><a href="/state">GET /state</a></li>
        <li><a href="/log/xkop">GET /log/xkop</a></li>
        <li><a href="/diag">GET /diag</a></li>
        </ul>
        </body></html>"""

def _as_int(v,d):
    try: return int(str(v).strip())
    except: return d

@app.post("/config")
def save_config():
    global CONFIG, XKOP_LISTEN_ADDR, XKOP_TX_ADDR, xkop_listener_sock, xkop_tcp_listener_sock
    cfg=request.get_json(force=True) or {}
    xkop_n=_as_int(cfg.get("xkop") or 1,1)
    preferred_xkop_prt=8000 + xkop_n

    # Ensure preferred port is within valid range (8001-8020)
    if preferred_xkop_prt < 8001 or preferred_xkop_prt > 8020:
        preferred_xkop_prt = 8001

    # Only search within 8001-8020 range
    max_attempts = 8020 - preferred_xkop_prt + 1
    xkop_prt=find_available_port(preferred_xkop_prt, max_attempts=max_attempts, check_both_protocols=True)

    # Verify final port is in valid range
    if xkop_prt < 8001 or xkop_prt > 8020:
        xkop_prt = preferred_xkop_prt  # Will fail with clear error

    if xkop_prt != preferred_xkop_prt:
        log_app(f"Port {preferred_xkop_prt} in use, using port {xkop_prt} instead")
        # Update xkop_n to reflect actual port allocated
        xkop_n = xkop_prt - 8000

    inst_prt=_as_int(cfg.get("snmp_port") or 161,161)
    CONFIG={"ip": (cfg.get("ip") or "").strip(), "instation_ip": (cfg.get("instation_ip") or "127.0.0.1").strip(),
        "xkop": xkop_n, "snmp_port": inst_prt, "rows": cfg.get("rows", [])}
    XKOP_LISTEN_ADDR=("0.0.0.0", xkop_prt)
    XKOP_TX_ADDR=(CONFIG["ip"] or "127.0.0.1", xkop_prt)
    with STATE_LOCK: seed_rows_from_config_locked()
    try:
        if xkop_listener_sock: xkop_listener_sock.close()
    except: pass
    try:
        if xkop_tcp_listener_sock: xkop_tcp_listener_sock.close()
    except: pass
    log_app(f"CFG: controller {XKOP_TX_ADDR[0]}:{XKOP_TX_ADDR[1]}")
    return jsonify({"ok":True,"listen":list(XKOP_LISTEN_ADDR),"tx":list(XKOP_TX_ADDR)})

@app.get("/config")
def get_config(): return jsonify(CONFIG)

@app.get("/state")
def get_state():
    global TEST_MODE, TEST_MODE_EXPIRY
    if TEST_MODE and TEST_MODE_EXPIRY and datetime.datetime.utcnow()>TEST_MODE_EXPIRY:
        TEST_MODE=False; TEST_MODE_EXPIRY=None
    with STATE_LOCK:
        return jsonify({"rows":STATE["rows"],"last_update":STATE["last_update"],"test_mode":TEST_MODE,
                        "expires": TEST_MODE_EXPIRY.isoformat() if TEST_MODE_EXPIRY else None})

@app.get("/test/mode")
def get_test_mode(): return jsonify({"enabled":TEST_MODE})

@app.post("/test/mode")
def set_test_mode():
    global TEST_MODE, TEST_MODE_EXPIRY
    data=request.get_json(force=True) or{}
    TEST_MODE=bool(data.get("enabled",False))
    if TEST_MODE:
        TEST_MODE_EXPIRY=datetime.datetime.utcnow()+datetime.timedelta(hours=1)
    else:
        TEST_MODE_EXPIRY=None
    return jsonify({"ok":True,"enabled":TEST_MODE})

@app.post("/test/input")
def test_input():
    data=request.get_json(force=True) or{}
    key=str(data.get("key","")).strip(); value=int(data.get("value",1))
    row=STATE["by_key"].get(key)
    if not row: return jsonify({"ok":False}),404

    try:
        in_idx_raw = row.get("in_idx", "0")
        # Handle comma-separated indices, take first one
        in_idx_parts = str(in_idx_raw).split(",")
        if not in_idx_parts or not in_idx_parts[0].strip():
            idx_byte = 0
        else:
            idx_byte = int(in_idx_parts[0].strip())
            # Validate index is in valid range (0-255)
            if idx_byte < 0 or idx_byte > 255:
                idx_byte = 0
    except (ValueError, IndexError, AttributeError):
        idx_byte = 0

    update_in_value(key,value)
    pkt=xkop_build_data([(idx_byte,value)])
    udp_send(pkt, XKOP_TX_ADDR)
    tcp_send(pkt)  # Also send via TCP when connected
    return jsonify({"ok":True})

@app.post("/test/output")
def test_output():
    data=request.get_json(force=True) or{}
    key=str(data.get("key","")).strip(); value=int(data.get("value",1))
    row=STATE["by_key"].get(key)
    if not row: return jsonify({"ok":False}),404
    update_out_value(key, value)
    return jsonify({"ok":True})

@app.get("/log/snmp")
def get_log_snmp():
    with LOG_LOCK: return jsonify(SNMP_LOG[-400:])

@app.get("/log/xkop")
def get_log_xkop():
    with LOG_LOCK: return jsonify(XKOP_LOG[-400:])

@app.get("/log/app")
def get_log_app():
    with LOG_LOCK: return jsonify(APP_LOG[-400:])

@app.get("/hvi")
def hvi():
    ip=(request.args.get("ip") or "").strip(); n=request.args.get("n") or "1"
    try: n=int(n)
    except: n=1
    if not ip: return ("Missing ip",400,{"Content-Type":"text/plain"})
    for fname in [f"XKOPMV{n}.hvi","XKOPMV1.hvi","XKOPMV5.hvi"]:
        url=f"http://{ip}/hvi?file={fname}"
        try:
            with urllib.request.urlopen(url, timeout=6) as resp: raw=resp.read()
            try: text=raw.decode("utf-8")
            except: text=raw.decode("latin-1","ignore")
            return (text,200,{"Content-Type":"text/plain; charset=utf-8","X-HVI-File":fname})
        except: pass
    return ("ERROR: could not fetch",502,{"Content-Type":"text/plain"})

@app.get("/diag")
def diag():
    return jsonify({"mode":"CLIENT","python_exe":sys.executable,"listen":list(XKOP_LISTEN_ADDR),
        "tx":list(XKOP_TX_ADDR),"rows_count":len(STATE["rows"])})

@app.get("/diag/network")
def diag_network():
    results = {}
    try:
        hostname = socket.gethostname(); local_ip = socket.gethostbyname(hostname)
        results["hostname"] = hostname; results["local_ip"] = local_ip
    except Exception as e: results["hostname_error"] = str(e)
    results["xkop_udp_listener_active"] = xkop_listener_sock is not None
    results["xkop_tcp_listener_active"] = xkop_tcp_listener_sock is not None
    return jsonify(results)

def start_threads():
    t1=threading.Thread(target=xkop_listener, daemon=True); t1.start()
    log_app("Started XKOP UDP listener")
    t2=threading.Thread(target=xkop_tcp_listener, daemon=True); t2.start()
    log_app("Started XKOP TCP client")

if __name__=="__main__":
    print("\n"+"="*60)
    print("XKOP Tool - CLIENT MODE")
    print("="*60)
    with STATE_LOCK: seed_rows_from_config_locked()

    # Find available XKOP port (limited to 8001-8020 range)
    preferred_xkop_port = 8000 + int(CONFIG.get("xkop",1))
    # Ensure preferred port is within valid range
    if preferred_xkop_port < 8001 or preferred_xkop_port > 8020:
        preferred_xkop_port = 8001

    # Only search within 8001-8020 range
    max_attempts = 8020 - preferred_xkop_port + 1
    xkop_prt = find_available_port(preferred_xkop_port, max_attempts=max_attempts, check_both_protocols=True)

    # Verify final port is in valid range
    if xkop_prt < 8001 or xkop_prt > 8020:
        xkop_prt = preferred_xkop_port  # Will fail with clear error

    if xkop_prt != preferred_xkop_port:
        print(f"⚠️  Port {preferred_xkop_port} in use, using port {xkop_prt} instead")
        # Update CONFIG to reflect actual port allocated
        CONFIG["xkop"] = xkop_prt - 8000

    # Flask port is always 5000 (start.sh kills any process using it)
    flask_port = 5000

    XKOP_LISTEN_ADDR = ("0.0.0.0", xkop_prt)
    XKOP_TX_ADDR = ((CONFIG.get("ip") or "127.0.0.1"), xkop_prt)
    start_threads()
    time.sleep(1)
    print(f"\nFlask on http://0.0.0.0:{flask_port}")
    print(f"XKOP UDP listening on {XKOP_LISTEN_ADDR[0]}:{XKOP_LISTEN_ADDR[1]}")
    print(f"XKOP TCP client connecting to controller {XKOP_TX_ADDR[0]}:{XKOP_TX_ADDR[1]}")
    print("="*60+"\n")
    app.run(host="0.0.0.0", port=flask_port, debug=False, threaded=True)
