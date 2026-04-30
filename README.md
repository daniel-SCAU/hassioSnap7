# hassioSnap7 – Home Assistant Snap7 PLC Integration

A Home Assistant custom integration that interfaces with **Siemens S7 PLCs** (S7-300, S7-400, S7-1200, S7-1500, …) using the [python-snap7](https://python-snap7.readthedocs.io/) library.

---

## Features

| Capability | Details |
|---|---|
| **Configurable IP** | Set (and later change via *Reconfigure*) the PLC IP address, rack, and slot |
| **M area tags** | Merker booleans, bytes, words, dwords |
| **DB area tags** | Data-Block booleans, bytes, words, dwords |
| **All numeric types** | `bool`, `byte`, `word`, `int`, `dword`, `dint`, `real` |
| **Read-only sensors** | Numeric → `sensor` entity; boolean → `binary_sensor` entity |
| **Writable boolean** | Mark a bool tag as *writable* → creates a `switch` entity |
| **Scan interval** | Configurable polling interval (default 30 s) |
| **UI-driven tag management** | Add / remove tags at any time through the HA options flow |

---

## Installation

### HACS (recommended)

1. Open HACS → *Integrations* → ⋮ → *Custom repositories*.
2. Add `https://github.com/daniel-SCAU/hassioSnap7` as an **Integration**.
3. Search for **Snap7 PLC** and install.
4. Restart Home Assistant.

### Manual

1. Copy the `custom_components/snap7_plc/` directory into your HA
   `config/custom_components/` folder.
2. Restart Home Assistant.

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration** and search for **Snap7 PLC**.
2. Enter the PLC connection details:

   | Field | Default | Description |
   |---|---|---|
   | PLC IP Address | — | IPv4 address of the PLC |
   | Rack Number | `0` | Rack number (usually 0) |
   | Slot Number | `1` | CPU slot (S7-1200/1500: 1, S7-300/400: 2) |
   | Scan Interval | `30` | Polling interval in seconds |

3. Click **Submit**. HA will verify the connection and create the device.

---

## Managing Tags

Open the integration's **Configure** dialog (Settings → Devices & Services → Snap7 PLC → *Configure*) to access the tag menu:

- **Add a new tag** – fill in a name, PLC address, and data type.
- **Remove existing tag(s)** – multi-select tags to delete.
- **Update scan interval** – change the polling rate without reconfiguring.
- **Save and close** – persist changes (triggers an integration reload).

### Supported Address Formats

| Area | Format | Example | Notes |
|---|---|---|---|
| Merker boolean | `M<byte>.<bit>` | `M0.0` | Creates a `binary_sensor` (or `switch` if writable) |
| Merker byte | `MB<byte>` | `MB10` | 8-bit unsigned |
| Merker word/int | `MW<byte>` | `MW20` | 16-bit; choose `word` (unsigned) or `int` (signed) |
| Merker dword/dint/real | `MD<byte>` | `MD100` | 32-bit; choose `dword`, `dint`, or `real` |
| Merker string | `MB<byte>(<length>)` | `MB140(4)` | Reads *length* consecutive bytes; each byte decoded as ASCII |
| DB boolean | `DB<n>.DBX<byte>.<bit>` | `DB1.DBX0.0` | |
| DB byte | `DB<n>.DBB<byte>` | `DB1.DBB2` | |
| DB word/int | `DB<n>.DBW<byte>` | `DB1.DBW4` | |
| DB dword/dint/real | `DB<n>.DBD<byte>` | `DB1.DBD8` | |
| DB string | `DB<n>.DBB<byte>(<length>)` | `DB1.DBB0(10)` | Reads *length* consecutive bytes; each byte decoded as ASCII |

---

## Changing the PLC IP

Go to **Settings → Devices & Services → Snap7 PLC → ⋮ → Reconfigure** to update the IP address, rack, slot, or scan interval at any time without losing your configured tags.

---

## Requirements

- Home Assistant 2024.1 or newer
- `python-snap7==1.3` (installed automatically)
- The PLC must have Ethernet access enabled (S7COMM or S7COMM+)
