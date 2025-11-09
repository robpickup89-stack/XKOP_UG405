# XKOP Controller Simulator for Windows

This script simulates a UG405 controller that sends DATA messages to your XKOP client via TCP.

## Features

- **Send DATA messages**: Push data updates to connected clients
- **4 Index Read Mode**: Automatically respond to client read requests for up to 4 indices
- **Internal state storage**: Maintain values for all 256 possible indices (0-255)
- **Interactive control**: Manually set index values and send custom packets
- **Auto-send mode**: Continuously send cycling data for testing

## Requirements

- Python 3.6 or later
- Windows (or any OS with Python)

## Quick Start

### 1. Run the Controller Simulator

On Windows, open PowerShell or Command Prompt and run:

```powershell
python windows_xkop_controller.py
```

The script will:
1. Start a TCP server on port 8001
2. Wait for your XKOP client to connect
3. Provide interactive or automatic sending modes

### 2. Configure Your XKOP Client

In your XKOP client's web interface (http://localhost:5000):
- Set the Controller IP to your computer's IP address (or `127.0.0.1` if running on same machine)
- Set XKOP port to 8001
- Configure output rows with indices matching what you'll send

### 3. Choose a Mode

When you run the simulator, it will ask you to choose a mode:

#### **Mode 1: Interactive** (Recommended for testing)
Manually send packets with custom values:

```
Command> s 0 1 1 0 3 1 4 0
```
This sends:
- Index 0, Value 1
- Index 1, Value 0
- Index 3, Value 1
- Index 4, Value 0

#### **Mode 2: Auto-send**
Automatically sends cycling values every N seconds (useful for continuous testing)

#### **Mode 3: CRC Test**
Verifies the CRC calculation is working correctly

## Interactive Commands

Once in interactive mode, use these commands:

### Send Custom Status
```
s <idx1> <val1> [idx2 val2] [idx3 val3] [idx4 val4]
```

Examples:
```
s 0 1                    # Single record: Index 0 = 1
s 0 100 1 200           # Two records
s 0 1 1 0 3 1 4 0      # Four records (your example)
```

### 4 Index Read Mode Commands

**Set Index Value** (for read responses):
```
i <index> <value>
```
Example:
```
i 0 100      # Set index 0 to value 100
i 5 1234     # Set index 5 to value 1234
```

**List All Index Values**:
```
l
```
Shows all currently set index values in the controller's memory.

**Get Specific Index Value**:
```
g <index>
```
Example:
```
g 0          # Get value for index 0
```

### How 4 Index Read Mode Works

When a client sends a DATA packet to the controller with specific indices:
1. The controller receives the packet and extracts the requested indices
2. The controller looks up the current values for those indices (defaults to 0 if not set)
3. The controller automatically sends a response packet with the current values

Example workflow:
```
# On controller:
Command> i 0 100        # Set index 0 = 100
Command> i 1 200        # Set index 1 = 200
Command> i 2 300        # Set index 2 = 300
Command> i 3 400        # Set index 3 = 400

# When client sends packet requesting indices [0, 1, 2, 3]:
# Controller automatically responds with values [100, 200, 300, 400]
```

### Send Predefined Scenarios
```
p <scenario_number>
```

Available scenarios:
- `p 1` - Your example: Index 0=1, 1=0, 3=1, 4=0
- `p 2` - All indices 0-3 with values 100-400
- `p 3` - Single record: Index 0=1
- `p 4` - All zeros
- `p 5` - Index 10=500, 20=1000

### Other Commands
- `t` - Run CRC test
- `q` - Quit

## Example Session

```
> python windows_xkop_controller.py

============================================================
XKOP Controller Simulator
============================================================
Listening on 0.0.0.0:8001
Waiting for client connection...
============================================================

Select mode:
  1 - Interactive mode (manual control)
  2 - Auto-send mode (periodic updates)
  3 - CRC test only

Mode (1-3)> 1

============================================================
INTERACTIVE MODE
============================================================
Commands:
  s <idx1> <val1> [idx2 val2] ... - Send status (max 4 records)
  p <scenario>                    - Send predefined scenario
  t                               - Run CRC test
  q                               - Quit
============================================================

✓ Client connected from 10.164.95.201:44250

Command> p 1
Sending scenario 1: Your example packet

Sent to client 10.164.95.201:44250:
  TX Packet:
  Hex: CA 35 02 00 00 01 01 00 00 03 00 01 04 00 00 XX XX
  Length: 17 bytes
  Header: 0xCA 0x35
  Type: 0x02 (STATUS)
  CRC: 0xXXXX (✓ Valid)
  Records (4):
    - Index   0, Value     1 (0x0001)
    - Index   1, Value     0 (0x0000)
    - Index   3, Value     1 (0x0001)
    - Index   4, Value     0 (0x0000)

Command> s 5 999
Sending custom packet...

Sent to client 10.164.95.201:44250:
  TX Packet:
  Hex: CA 35 02 05 03 E7 FF 00 00 FF 00 00 FF 00 00 XX XX
  Length: 17 bytes
  Header: 0xCA 0x35
  Type: 0x02 (STATUS)
  CRC: 0xXXXX (✓ Valid)
  Records (1):
    - Index   5, Value   999 (0x03E7)

Command> q
```

## Testing CRC Calculation

To verify the CRC implementation matches your specification:

```powershell
python windows_xkop_controller.py --test-crc
```

This will build your example packet and verify the CRC is calculated correctly.

## Packet Format

Every XKOP STATUS packet is exactly **17 bytes**:

```
Byte 0:     0xCA             (Header 1)
Byte 1:     0x35             (Header 2)
Byte 2:     0x02             (Type: STATUS)
Bytes 3-14: 12 bytes         (4 records × 3 bytes each)
Bytes 15-16: CRC16           (Big-endian)
```

Each record (3 bytes):
```
Byte 0: Index (0-255)
Byte 1: Value MSB (high byte)
Byte 2: Value LSB (low byte)
```

Empty slots use: `0xFF 0x00 0x00`

## Troubleshooting

### Port Already in Use
If port 8001 is already in use, edit the script and change:
```python
controller = XKOPController(host='0.0.0.0', port=8002)
```

### Client Not Connecting
- Check firewall settings
- Verify the IP address in your XKOP client config
- Ensure both are on the same network (or use 127.0.0.1 for local testing)

### No Output in Client
- Check that your XKOP client has rows configured with matching `out_idx` values
- Verify the client is connected (check logs at http://localhost:5000)
- Check XKOP logs in the web interface

## Notes

- The CRC calculation exactly matches your C specification
- The script validates all outgoing CRCs
- Can handle multiple send commands while client is connected
- Thread-safe for concurrent operations
- Compatible with Windows, Linux, and macOS
