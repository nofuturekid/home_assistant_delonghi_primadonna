## How to Enable Debug Logs
To see the debug information in Home Assistant, you need to configure the `logger` component.

1. Permanent Configuration (Recommended)
Add the following to your `configuration.yaml` file and restart Home Assistant:

```yaml
logger:
  default: warning
  logs:
    custom_components.delonghi_primadonna: debug
```
2. Temporary Configuration (No Restart)
You can use the `logger.set_level` service to enable debug logs immediately without restarting:

Go to `Developer Tools` > `Services`.
Select the `logger.set_level` service.
Use the following YAML:
```yaml
custom_components.delonghi_primadonna: debug
```
Click **Call Service**.

## These are debug notes collected from the device

Please join

|Code                                                    | Details                            |
|--------------------------------------------------------|------------------------------------|
|d0 12 75 0f 01 05 00 00 00 07 00 00 00 00 00 00 00 9d 61|All is good                         |
|d0 12 75 0f 01 15 00 00 00 07 00 00 00 00 00 00 00 aa 31|No water tank                       |
|d0 12 75 0f 01 0d 00 00 00 07 00 00 00 00 00 00 00 86 c9|No recycle tank                     |
|d0 12 75 0f 01 01 00 00 00 00 03 00 00 00 00 00 00 8f 2f|Power off                           |
|d0 12 75 0f 01 01 00 00 00 00 03 64 00 00 00 00 00 d6 96|Power off                           |
|d0 12 75 0f 01 01 00 00 00 01 07 64 00 00 00 00 00 50 83|Turning on                          |
|d0 12 75 0f 01 45 00 01 00 07 00 00 00 00 00 00 00 2f 64|Requested fresh water               |
|d0 12 75 0f 01 03 00 00 00 01 05 08 00 00 00 00 00 62 71|Washing I suppose                   |
|d0 12 75 0f 01 01 00 00 00 01 01 00 00 00 00 00 00 a8 1f|Heat water                          |
|d0 12 75 0f 01 03 00 00 00 01 05 61 00 00 00 00 00 75 8b|Device is ready notification        |
|d0 12 75 0f 01 01 00 04 00 00 03 64 00 00 00 00 00 7b a3|Power off device asks for cleanup   |

|Codes for Dinamica Plus                                 | Details                            |Notification|
|--------------------------------------------------------|------------------------------------|------------|
|**Sequences**|||
|d0 12 75 0f 02 00 01 00 00 01 01 00 00 00 00 00 00 bc 86|Sequence 1 - Powered on             ||
|d0 12 75 0f 02 02 01 00 00 01 05 1d 00 00 00 00 00 2f 6d|Sequence 2 - Unknown?               ||
|d0 12 75 0f 02 00 01 00 00 01 07 64 00 00 00 00 00 44 1a|Sequence 3 - Unknown?               ||
|d0 12 75 0f 02 04 01 00 00 07 00 00 00 00 00 00 00 89 f8|Sequence 4 - Ready (`Milk Carafe` is in the `Frothing` position)||
|d0 12 75 0f 02 00 01 00 00 00 03 64 00 00 00 00 00 c2 0f|Sequence 5 - Power off              ||
|**Cleaning**|||
|d0 12 75 0f 04 05 01 00 40 0c 03 0d 00 00 00 00 00 1a 51|Started cleaning `Milk Carafe` spout (nozzle in `Clean` position)||
|d0 12 75 0f 04 05 01 00 00 07 00 00 00 00 00 00 00 05 e6|Finished cleaning `Milk Carafe` spout (nozzle in `Clean` position)||
|d0 12 75 0f 02 00 01 00 00 08 02 00 00 00 00 00 00 3d 0d|Started `rinsing` machine||
|d0 12 75 0f 02 02 01 00 00 08 05 43 00 00 00 00 00 86 53|Finished `rinsing` machine - Unknown?||
|**Insert / Remove**|||
|                                                        |Inserted `Water Tank`               |DeviceOK|
|d0 12 75 0f 01 15 00 00 00 01 00 00 00 00 00 00 00 2a fa|Removed `Water Tank`                |NoWaterTank|
|                                                        |Inserted `Hot Water Nozzle`         ||
|d0 12 75 0f 00 04 00 00 00 07 00 00 00 00 00 00 00 db 77|Removed `Hot Water Nozzle`          ||
|**Beverages**|||
|d0 12 75 0f 01 05 00 00 00 0b 03 07 00 00 00 00 00 9c 15|Started `Hot Water` beverage        ||
|d0 12 75 0f 02 04 01 00 00 0a 02 00 00 00 00 00 00 bf 7f|Starting `Latte Machiato` beverage?||
|d0 12 75 0f 02 00 01 00 40 07 0e 64 00 00 00 00 00 b0 c4|Finished / cancelled `unknown` beverage?||
|**Profiles**|||
|d0 07 a9 f0 01 00 3b 3c|Set Profile 1 response||
|d0 07 a9 f0 02 00 6e 6f|Set Profile 2 response||
|d0 07 a9 f0 03 00 5d 5e|Set Profile 3 response||
|d0 07 a9 f0 04 01 d4 e8|Profile 4 **rejected**|Byte 5 is the status: `00` accepted, `01` rejected. Previously mislabelled as a "Guest" response - that machine refused slot 4.|

### Management protocol

### The commands have a request and response id

The request id is the third byte of the command, the response id must be the same as request id.
|Request ID|Purpose                                              |
|----------|-----------------------------------------------------|
| 0x75     | Device status                                       |
| 0x83     | Prepare or manage beverage                          |
| 0x84     | Power on command                                    |
| 0x90     | Manage device settings                              |
| 0x95     | Read a settings parameter                           |
| 0xa2     | Statistics request/response                         |
| 0xa3     | Checksum                                            |
| 0xa4     | Request profile list (answered only while awake)    |
| 0xa5     | Write profile names                                 |
| 0xa9     | Switch the user profile                             |
| 0xaa     | Read recipe names (same layout as 0xa4)             |
| 0xd2     | Read the machine PIN                                |
| 0xa1     | Read a parameter, extended form                     |
| 0xa6     | Read a recipe quantity for one profile              |
| 0xa8     | Read recipe priorities                              |
| 0xab     | Write recipe names                                  |
| 0xad     | Set favourite beverages                             |
| 0xb0     | Read min/max bounds for a beverage                  |
| 0xb1     | Set the machine PIN                                 |
| 0xb9-0xbb| Bean system select / read / write                   |
| 0xe2     | Set the clock                                       |

Numbers cross-checked against longshot's `EcamRequestId`.

### Verified on an ECAM 656.55.MS, 2026-08-22

A full descaling run plus filter change, milk-system cleaning and steam
dispensing were captured over the 0x75 status frame.

**Machine states (byte 9)** - four values measured directly, correcting the
previous table: `4` = descaling program (set from the moment the program is
armed until it ends, including while pumping - previously mapped to "heating"),
`5` = steam dispensing (96 s, full progress curve - previously "ready"),
`12` = milk system cleaning (~24 s), `14` = filter change program (previously
carrying the "descaling" label that belongs to 4). Only `6` remains unverified.

**Byte 8 bit 0x08** mirrors the running program: it appeared in the very same
frame as state 4 and cleared with the program end.

**Byte 11** is progress in percent, but the descaling program never populates it
(constant 00). Steam, milk cleaning and heat-up do. A remaining-time display for
descaling is therefore not possible.

**Byte 4 is a mechanical coding pin, not a presence sensor.** The attachment is
inserted from the front and carries a pin whose insertion depth is measured:
`00` none, `01` water spout / steam nozzle, `02` milk container, `04` milk
container with the knob on CLEAN. The value reflects the position, not the
activity - `04` persists after the cleaning program has finished. The three foam
levels are purely mechanical and invisible in the protocol.

**Only one missing part is reported at a time.** With both the water tank and
the grounds container removed, only bit 0x08 (grounds container) was set; bit
0x10 (water tank) appeared only after the container was back in. The display
behaves identically. A "water tank missing" sensor therefore stays silent while
the grounds container is also missing - which is the normal case during
descaling. This cannot be fixed in the integration; the information is not sent.
Brew group and side door produce no bit at all, though this could not be proven
independently: both are only accessible with the tank removed, so their bit
would always be masked by 0x10.

**Send rate:** 266 measured intervals show a fixed `12 24 24` pattern - a
60-second period, three frames per minute while idle, switching to a steady 12 s
during a dispense. There is not a single 36 s gap, which rules out packet loss.
Consequence: a 25-30 s espresso may fall into a single frame or none at all, so
a live dispensing sensor can never be fully reliable.

**Opcode 0xa3** requires flag byte `f0`; with `0f` there is no reply. It returns
16 data bytes on this machine, contrary to longshot's `Checksum() => ()`. The
value stayed byte-identical across the whole maintenance cycle and across a
configuration change, so it covers neither statistics nor settings.

**Alarms take precedence over the machine state** in the status sensor, and at
least one alarm is almost always pending - which is why a corrected state
mapping stays invisible in normal operation.

**A reply carries the id of its request.** Unsolicited status frames
(`0x75`) arrive every few seconds while the machine is awake, so a
pending request must only be considered answered by a frame with a
matching id. `0x84` (power) and `0xe2` (clock) are never answered at
all - waiting for them only blocks the device lock.

Switches managed by command [0x0d, 0x0b, 0x90, 0x0f, 0x00, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
The nine digit (counted from 0) is the command bitmask

### Notification Protocol assumptions
|Code    | Details                                             |
|--------|-----------------------------------------------------|
|00 - 03 | was not changed suspect pilot or device type
|04      | nozzle sensor hot water, milk pot or detached
|05      | General notification bitmask is suspected
|        | 0
|        | 1
|        | 2
|        | 3
|        | 4
|        | 5
|        | 6
|        | 7
|06      | Ability to use milk pot, maybe
|07      | Service notification bitmask is suspected
|        | 0
|        | 1
|        | 2 - descale
|        | 3 - replace water filter
|        | 4
|        | 5
|        | 6
|        | 7
|08      | always 0
|09      | 0x00 if device active 0x07 if device is off
|10      | cooking progress stage
|11      | progress bar inside the stage
|12 - 16 | always 0 perhaps for the new features
|17 - 18 | Signature
|99      | Always 0

### Statistics Protocol (0xA2)

This command is used to request various counters (beverages, maintenance, etc.) from the machine.

#### Request Format
`[0x0D, 0x08, 0xA2, 0x0F, ID_HI, ID_LO, COUNT, CRC_HI, CRC_LO]`
- `ID_HI/LO`: Starting parameter ID (e.g., `0x00 0x64` for ID 100).
- `COUNT`: Number of parameters to return.

#### Response Format
`[0xD0, LEN, 0xA2, 0x0F, ID_HI, ID_LO, VAL_B3, VAL_B2, VAL_B1, VAL_B0, ...]`
- **Implicit ID**: The first 4 bytes of value (`VAL_B3..B0`) belong to the ID requested in bytes 4-5.
- **Explicit ID**: Subsequent values are formatted as `[ID_HI, ID_LO, VAL_B3, VAL_B2, VAL_B1, VAL_B0]`.

**NOTE**: All multi-byte values (IDs and Counters) are **Big Endian**.
- `ID_HI` is the most significant byte.
- `VAL_B3` is the most significant byte of the 32-bit integer value.

> [!WARNING]
> **Decoding Bug**: Ensure you skip the bytes 4-5 when reading the first value. If you read from byte 4 as a 4-byte integer, you will get a value like `196673536` for ID 3000 (which is `0x0B B8 << 16`).

#### Parameter ID Map

| ID | Category | Description | Notes |
|----|----------|-------------|-------|
| 105 | Maintenance | Descaling Count | |
| 106 | Maintenance | Total Water Quantity | Divide by 2000 for Liters |
| 108 | Maintenance | Filter Replacements | |
| 111 | Maintenance | Milk Cleaning Count | |
| 3000 | Beverage | Black Coffee Total (Part 1) | Combine with 3077 |
| 3001 | Beverage | Coffee with Milk Total (Part 1) | Combine with 3003 |
| 3003 | Beverage | Coffee with Milk Total (Part 2) | Combined as ID -3003 |
| 3017 | Beverage | Total with Cold Milk | `TOTAL_BEVERAGE_WITH_COLD_MILK` in APK |
| 3021 | Beverage | Total Choco | `TOTAL_CHOCO` in APK |
| 3025 | Beverage | Total Tea | `TOTAL_TEA` in APK |
| 3047 | Beverage | Total "To Go" (Part 1) | Combine with 3048 |
| 3048 | Beverage | Total "To Go" (Part 2) | |
| 3077 | Beverage | Black Coffee Total (Part 2) | Combined as ID -3077 |
| 3078 | Beverage | Total Beverage (Part 2?) | |
| 3080 | Beverage | Total Beverage (Part 1?) | |

**Combined Calculations:**
- **Total Black Coffee**: `ID 3000` + `ID 3077` (Result stored as `-3077`)
- **Total Coffee with Milk**: `ID 3001` + `ID 3003` (Result stored as `-3003`)
- **Total To-Go**: `ID 3047` + `ID 3048`
- **Other Beverage**: `ID 3080` + `ID 3078`

> [!NOTE]
> **The Milk Cleaning ID Discrepancy**
> Analysis of the decompiled APK (`b7.e.java` line 508) shows that the official app requests **ID 115** for the milk cleaning counter. However, some integration users have reported that their machines provide this value on **ID 111**. The current implementation uses 111, but 115 is worth investigating if 111 returns 0.

### Profile list (0xa4)

Captured 2026-08-20 on a machine with six profiles.

**Only answered while the machine is awake.** In standby it stays silent -
not even a status frame comes back - so the request times out. Statistics
(`0xa2`) and settings (`0x95`) *are* answered in standby, which is what
makes the difference easy to miss.

Request, reading a range of profiles (`<start> <end>`, inclusive):

```
0d 07 a4 f0 01 03 d8 2e     profiles 1-3
0d 07 a4 f0 04 06 77 7e     profiles 4-6
```

Response, ~250 ms later:

```
d0 44 a4 f0 00 4e 00 69 00 63 00 6f 00 6c 00 65 00 00 00 00 00 00 00 00 08
            00 54 00 68 00 6f 00 6d 00 61 00 73 00 00 00 00 00 00 00 00 05
            00 42 00 45 00 33 00 2f 00 42 00 45 00 4e 00 55 00 54 00 5a 03  a4 1c
```

Layout: 4 byte header, then one 21-byte record per profile, then 2 byte CRC.
The length byte (`0x44` = 68) is the total frame length minus one.

Each record is 10 characters UTF-16 big-endian, padded with NUL, followed by
one byte:

| Record | Name | Last byte |
|---|---|---|
| 1 | `Nicole` | `0x08` |
| 2 | `Thomas` | `0x05` |
| 3 | `BE3/BENUTZ` | `0x03` |
| 4-6 | `BE4/BENUTZ` … | `0x03` |

The last byte is the **icon** shown for that profile. The two personalised
profiles carry different values while all four factory profiles share one,
which rules out a simple "configured" flag. Independently confirmed by
[longshot](https://github.com/mmastrac/longshot), which decodes the same
structure as `WideStringWithIcon { name: String, icon: u8 }` and uses it for
both `ProfileNameRead` and `RecipeNameRead`. The icon values themselves are
not enumerated there.

Names are truncated to the 10 character field: the factory name is
`BE3/BENUTZER`, the machine reports `BE3/BENUTZ`.

The response carries no index, so the reader has to remember which range it
asked for.

### Machine state (byte 9 of a 0x75 frame)

Measured 2026-08-20 across a full power cycle, with the percentage in
byte 11 and the stage counter in byte 10:

```
19:31:23   status 07                    ready
           -- power off sent 19:31:30 --
19:31:35   status 02  stage 01          shutting down

           -- power on sent 19:40:43 --
19:40:53   status 01  stage 02    0 %   turning on
19:41:04   status 01  stage 05   54 %
19:41:17   status 01  stage 07  100 %
19:41:29   status 07                    ready
```

So **2 is shutting down, not washing**, and 1 covers the whole warm-up
rather than being a momentary state. Byte 5 alternates between `0x02`
(MotorUp) and `0x04` (MotorDown) during the rinse, resting at `0x04`.

Values 4, 5, 6 and 14 remain unverified and disagree with longshot,
which has 4 Descaling, 5 SteamPreparation, 6 Recovery and no 14 (but
16 ChocolatePreparation).
