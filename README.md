# hassioSnap7 – Home Assistant Snap7 PLC Integration

A Home Assistant custom integration that interfaces with **Siemens S7 PLCs** (S7-300, S7-400, S7-1200, S7-1500, …) using the [python-snap7](https://python-snap7.readthedocs.io/) library.

---

## Features

| Capability | Details |
|---|---|
| **Configurable IP** | Set (and later change via *Reconfigure*) the PLC IP address, rack, and slot |
| **M area tags** | Merker booleans, bytes, words, dwords |
| **DB area tags** | Data-Block booleans, bytes, words, dwords |
| **I area tags** | Process-input booleans, bytes, words, dwords (read-only) |
| **Q area tags** | Process-output booleans, bytes, words, dwords (readable and writable) |
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
   | Scan Interval | `30000` | Polling interval in **milliseconds** (e.g. 30000 = 30 s) |

3. Click **Submit**. HA will verify the connection and create the device.

---

## Managing Tags

Open the integration's **Configure** dialog (Settings → Devices & Services → Snap7 PLC → *Configure*) to access the tag menu:

- **Add a new tag** – fill in a name, PLC address, and data type.
- **Remove existing tag(s)** – multi-select tags to delete.
- **Import tags from YAML** – paste a YAML tag list to merge into existing tags.
- **Export tags to YAML** – view the current tag list as copyable YAML.
- **Update scan interval** – change the polling rate without reconfiguring.
- **Save and close** – persist changes (triggers an integration reload).

### YAML Import / Export

Tags can be bulk-managed using YAML.  The expected format is:

```yaml
tags:
  - id: <uuid>           # optional – generated if omitted
    name: Temperature
    address: DB1.DBD0
    data_type: real
    unit: "°C"
    writable: false
```

A top-level list (without the `tags:` key) is also accepted.

**Import (merge) behavior:**
- Matching uses `id` first, then `(name, address)` as a fallback key.
- Matched tags are updated with the imported fields.
- Unmatched imported tags are appended as new tags.
- Existing tags not referenced by the import are kept unchanged.
- Invalid YAML or invalid tag fields show a clear error and keep you on the import screen.

**Deleted tag cleanup:**
When tags are removed (via the *Remove* step or by importing a revised list and then saving), their corresponding Home Assistant entities are removed from the entity registry on the next integration reload so no stale entities remain.

### Supported Address Formats

| Area | Format | Example | Notes |
|---|---|---|---|
| Merker boolean | `M<byte>.<bit>` | `M0.0` | Creates a `binary_sensor` (or `switch` if writable) |
| Merker byte | `MB<byte>` | `MB10` | 8-bit unsigned |
| Merker word/int | `MW<byte>` | `MW20` | 16-bit; choose `word` (unsigned) or `int` (signed) |
| Merker dword/dint/real | `MD<byte>` | `MD100` | 32-bit; choose `dword`, `dint`, or `real` |
| Merker string | `MB<byte>(<length>)` | `MB140(4)` | Reads *length* consecutive bytes as a raw ASCII byte array (not Siemens S7 STRING format) |
| DB boolean | `DB<n>.DBX<byte>.<bit>` | `DB1.DBX0.0` | |
| DB byte | `DB<n>.DBB<byte>` | `DB1.DBB2` | |
| DB word/int | `DB<n>.DBW<byte>` | `DB1.DBW4` | |
| DB dword/dint/real | `DB<n>.DBD<byte>` | `DB1.DBD8` | |
| DB raw ASCII bytes | `DB<n>.DBB<byte>(<length>)` | `DB1.DBB0(10)` | Reads *length* consecutive bytes as a raw ASCII byte array (not Siemens S7 STRING format) |
| Input boolean | `I<byte>.<bit>` | `I0.0` | Process input area – **read-only** |
| Input byte | `IB<byte>` | `IB10` | Process input area – **read-only** |
| Input word/int | `IW<byte>` | `IW20` | Process input area – **read-only** |
| Input dword/dint/real | `ID<byte>` | `ID100` | Process input area – **read-only** |
| Output boolean | `Q<byte>.<bit>` | `Q0.0` | Process output area; creates a `switch` if writable |
| Output byte | `QB<byte>` | `QB10` | Process output area; writable |
| Output word/int | `QW<byte>` | `QW20` | Process output area; writable |
| Output dword/dint/real | `QD<byte>` | `QD100` | Process output area; writable |

> **Note:** I area addresses are **read-only** – attempting to write to an I address will raise an error.  Q area addresses support both reads and writes.

---

## Changing the PLC IP

Go to **Settings → Devices & Services → Snap7 PLC → ⋮ → Reconfigure** to update the IP address, rack, slot, or scan interval at any time without losing your configured tags.

---

## Requirements

- Home Assistant 2024.1 or newer
- `python-snap7==1.3` (installed automatically)
- The PLC must have Ethernet access enabled (S7COMM or S7COMM+)
