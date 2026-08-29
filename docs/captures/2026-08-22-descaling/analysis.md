# De'Longhi ECAM 656.55.MS — BLE capture 2026-08-22, 17:14–20:00

Full descaling run plus filter change, milk-system cleaning and steam
dispensing, captured over the 0x75 status frame.
Raw data: `frames-*.log`. Frame layout: `d0 12 75 0f b4 b5 b6 b7 b8 b9 b10 b11 … crc crc`

## Machine state (byte 9) — four values measured for the first time

| Value  | Meaning                      | Evidence                         |
| ------ | ---------------------------- | -------------------------------- |
| 0      | StandBy                      | previously known                 |
| 1      | TurningOn / heating          | 18:23:38, byte 11 = 0x64 = 100 % |
| 2      | ShuttingDown                 | previously known                 |
| **4**  | **descaling program active** | 17:20:26 – 18:23:38              |
| **5**  | **steam dispensing**         | 19:43, 96 s, full progress curve |
| 7      | Ready                        | throughout, before and after     |
| 8      | Rinsing                      | previously known                 |
| **12** | **milk system cleaning**     | 18:50:38, ~24 s, knob on CLEAN   |
| **14** | **filter change program**    | 18:32:02                         |

State 4 is already set _before_ the run starts (as soon as all preparations are
done) and stays set while pumping — it is the program state, not "descaling right
now". The filter change gets its own top-level state because it is a separate
program in the machine's own menu structure, not a sub-phase of 4.

## sub_status (byte 10) — phases within a program

| Value | Phase                                   | From                     |
| ----- | --------------------------------------- | ------------------------ |
| 00    | idle                                    | —                        |
| 02    | preparation (also during a dispense)    | 18:32:02, 19:43:02       |
| 03    | program ready, waiting for start        | 17:20:26                 |
| 04    | running (descaling / dispensing)        | 17:24:14                 |
| 06    | finishing a dispense                    | 19:44:38                 |
| 07    | wrap-up / insert filter                 | 18:10:02                 |
| 08    | refill water / waiting for confirmation | 17:58:14                 |
| 09    | rinse cycle                             | 18:04:14, again 18:13:50 |
| 0x11  | program completion                      | 18:18:50                 |

## Byte 5 — switches (low byte of `data[5] + (data[6] << 8)`)

| Bit  | Meaning                                       | Evidence                                         |
| ---- | --------------------------------------------- | ------------------------------------------------ |
| 0x01 | water path active through the attachment      | steam nozzle and CLEAN, not plain milk container |
| 0x02 | brew group in working position → coffee spout | 17:24:14, 18:04:14                               |
| 0x04 | brew group at rest → hot water / steam nozzle | 17:24:50, 18:06:14, 18:13:50                     |
| 0x08 | drip tray / grounds container unit removed    | 17:18:14 on, 17:20:14 off                        |
| 0x10 | water tank removed                            | 4× confirmed in both directions                  |
| 0x40 | out of water                                  | 17:57:02, 18:09:50, 18:18:38                     |

Byte 6 bit 0x01 (i.e. 0x100 of the combined switch word) marks the milk
container being attached.

`motor_down` as a label for bit 0x04 is misleading: it is not a permanent state
but the resting position of the brew group. 0x02 and 0x04 are mutually
exclusive. Drip tray and grounds container are mechanically coupled — the
machine cannot report anything finer than "unit removed".

## Byte 7 — alarms

| Bit  | Meaning              | Evidence                                     |
| ---- | -------------------- | -------------------------------------------- |
| 0x01 | water tank empty     | 17:57:02 ↔ `empty_water_tank`                |
| 0x04 | descaling due        | set since the previous day, cleared 18:18:50 |
| 0x08 | replace water filter | 18:04:38 ↔ `replace_water_filter`            |

**Alarms take precedence over the machine state in the status sensor.** HA showed
the highest-priority alarm throughout and never state 4. Observed sequence:
descale_alarm → empty_water_tank → descale_alarm → replace_water_filter → ready.
This is why the state mapping fix was never visible in normal operation.

## Byte 8 — program running flag

Bit 0x08 appeared in the very same frame as state 4 (17:20:26) and cleared with
the program end (18:19:50). It mirrors the program state.

## Byte 11 — progress in percent

Zero throughout the descaling program — that program does not populate the
field. Steam dispensing, milk cleaning and heat-up do: steam ran 1 → 8 → 22 →
35 → 48 → 61 → 74 → 88 → 100 across eight frames. So the field works; descaling
simply does not use it. A remaining-time display for descaling is not possible.

## Byte 4 — mechanical coding pin, NOT a presence sensor

The attachment is inserted from the front and carries a pin whose insertion
depth the machine measures. The milk container has the same pin, shaped
differently; the CLEAN position pushes it in further.

| Value | Attachment                    |
| ----- | ----------------------------- |
| 00    | none detected                 |
| 01    | water spout / steam nozzle    |
| 02    | milk container                |
| 04    | milk container, knob on CLEAN |

Byte 4 reflects the _position_, not the activity: value 04 persists after the
cleaning program has finished. The program is triggered by turning the knob
(edge), not by the state. The three foam levels are purely mechanical (air
intake inside the container) and invisible in the protocol — frames were
bit-identical across them.

## What the frame does NOT expose

- **Pump strokes.** Verified repeatedly in both directions: pause and active
  pumping are bit-identical, as are continuous flow and short bursts. At a frame
  rate of 12–24 s it could not be resolved anyway.
- **Menu navigation / waiting for user input.** No dedicated state value,
  confirmed three times. Only _what_ is missing shows up (alarm bits), never
  _that_ the machine is waiting. A "needs attention" sensor would have to be
  built from the alarm bits.
- **Remote commands failing.** Starting a beverage while byte 4 is 00 is
  discarded silently — no error, no log entry. Only the display shows
  "insert water spout". Automations must verify the state actually changes.

## Frame rate

266 measured intervals: 12 s (135×), 24 s (122×), 36 s (**0×**).
The sequence follows a fixed pattern `12 24 24 | 12 24 24 | …` — a 60-second
period, three frames per minute while idle. During a dispense the machine
switches to a steady 12 s.

**This is not packet loss.** Random radio loss would scatter the intervals and
inevitably produce 36 s and 48 s gaps; there is not a single one. The
ESP32/ESPHome proxy sits directly next to the machine and the log shows zero
timeouts and no disconnects over the whole session.

Consequence for a live dispensing sensor: an espresso of 25–30 s falls into one
or two frames at best, possibly none. Not an integration problem — the machine
simply does not send often enough. Counting dispenses via `total_coffee` is more
robust than a live sensor.

## Opcode 0xa3 (Checksum)

Request `0d 05 a3 f0 00 00` (the integration fills in the CRC).
**The flag byte must be f0** — with 0f there is no reply (10 s timeout). This
confirms longshot's rule `if self.is_response_required() { out.push(0xf0) }`.

Response, byte-identical at 17:10, 17:11, 18:34, 18:37 and 18:40:

    d0 15 a3 f0 b0 96 73 0f de d0 d6 ec de d0 de d0 56 47 48 e2 82 67

16 data bytes; as 16-bit BE: b096 730f ded0 d6ec ded0 ded0 5647 48e2.
longshot declares `Checksum() => ()`, i.e. no response payload — demonstrably
incomplete for the 656.55.

Unchanged across the entire maintenance cycle (descaling_count 20→21,
filter_replacements 8→9, +5.7 l of water) **and** across a configuration change
(water filter switched off in the menu, 18:37). So it covers neither statistics
nor configuration; firmware/model identification is what remains.
Open: it may only be recomputed at device start — a query after the next power
cycle would settle that.

## Counters

| Counter             | Before    | After     | At                 |
| ------------------- | --------- | --------- | ------------------ |
| descaling_count     | 20        | 21        | 18:19:13           |
| filter_replacements | 8         | 9         | 18:34:13           |
| total_water         | 1047.91 l | 1053.62 l | +5.7 l for the run |

**Statistics blocks are read at different times.** total_water updated at
18:33:13, filter_replacements only at 18:34:13. After an action, wait at least a
minute before concluding anything from an unchanged counter value.

## Sensor latency

HA sensors trail the raw frames by 5–30 s (measured: +23, +17, +29, +11, +5 s).
Do not measure immediately after a frame and then claim "the sensor does not
react" — that mistake happened twice during this session.

## Only one missing part is reported at a time (20:35-20:50)

Measured while the machine was cleaned out after the run:

| Time | Missing | b5 |
|------|---------|-----|
| 20:41 | water tank **and** grounds container | `08` — tank bit absent |
| 20:45 | water tank only | `10` |
| 20:48 | water tank only (brew group + door restored) | `10`, unchanged |
| 20:50 | nothing | `00` |

With both parts out, only bit 0x08 was set; bit 0x10 appeared only after the
container was back in. The display behaves identically — with both missing it
reports only "grounds container". So the bits are **not independent**: the
machine reports a single condition at a time, grounds container ranking above
water tank.

Consequence: a "water tank missing" sensor stays silent whenever the grounds
container is also missing — which is exactly what happens during descaling.
Not fixable in the integration; the information is never sent.

**Brew group and side door produce no bit** — restoring both changed nothing.
This is NOT independently proven though: both are only reachable with the tank
removed, so any bit of theirs would always be masked by 0x10. Testable by
removing only the brew group, closing the door and reinserting the tank.

**sub_status distinguishes standby variants:** `03` while the display was on and
something was missing, `02` once everything was in place and the display had
switched itself off. This also explains the older note that "progress is
non-zero in standby" — it was not progress but the display indicator.

Caveat on all of the above: the machine wakes partially when a part is removed
in standby, so its exact operating state during these measurements is unknown.

## Device fault found along the way

The steam nozzle is pushed out by about 1 mm under pressure, a visible gap
appears, the coding pin leaves its position, byte 4 drops to 00 and the machine
aborts the dispense. Pressing it back in produces the machine's confirmation
tone, so the detection itself works perfectly.

| Dispense | Counter-pressure              | Result                              |
| -------- | ----------------------------- | ----------------------------------- |
| 18:56    | no                            | 100 % (only clean one without help) |
| 19:11    | no                            | aborted at 46 %                     |
| 19:27    | no                            | user-cancelled at 43 %              |
| 19:28    | no                            | machine aborted at 2 %              |
| 19:43    | **yes**                       | **100 %, 96 s**                     |
| 19:50    | no, after cleaning the nozzle | completed                           |
| 19:57    | no                            | **aborted at 68 %**                 |

Nozzle cleaned, nothing visible found; the last run aborted again, so cleaning
did not fix it. Latch and both O-rings look intact and still grip noticeably.
The retaining mechanism or the attachment itself remains the suspect.

Useful side effect: `nozzle_status` shows the disconnect in real time, so an
automation "nozzle_status becomes detached during a dispense" would be a
workable warning.

---

# Changes needed in the fork

Repository: `nofuturekid/home_assistant_delonghi_primadonna`, branch `maintained`.

## 1. `const.py` — MACHINE_STATUS is wrong, not just incomplete

```python
 4: "heating",              # measured: descaling program
 5: "ready",                # measured: steam dispensing
14: "descaling",            # measured: filter change program
```

`5: "ready"` is the worst of the three: during a 96-second steam dispense the
status sensor reports "ready". And value 14 currently carries the label that
belongs to 4. Proposed:

```python
 4: "descaling",
 5: "steam",                 # needs a translation key
12: "cleaning_milk_spout",   # already correct
14: "changing_filter",       # needs a translation key
```

The comment above the table (lines 100–103) claims 4, 5, 6 and 14 are
unverified. Three of them now are; only 6 remains open.
New translation keys are required in `translations/*.json`.

## 2. `device.py` — dispensing condition misses most dispenses

Current (around line 868):

```python
self.is_dispensing = (
    monitor_data.status in (10, 11)
    or (monitor_data.status == 7 and monitor_data.sub_status != 0)
)
```

Steam runs under state 5, milk cleaning under 12 — neither is covered, and the
sensor stayed `off` all evening despite two full steam dispenses with clean
progress curves. State 7 with a non-zero sub_status turned out never to occur
during the observed dispenses.

Suggestion: include 5, and decide deliberately whether maintenance programs
(12, 14) should count as "dispensing" or deserve a separate `busy` sensor.
My preference is a separate sensor — a milk-system rinse is not a beverage.

Note the inherent limit: at three frames per minute while idle, short dispenses
may produce no frame at all. The sensor can never be fully reliable.

## 3. `const.py` — rename the switch bit label

`motor_down` for bit 0x04 describes a resting position, not a permanent state.
It only looked permanent because the machine was idle whenever it was observed.

## 4. Worth documenting in DEBUG_NOTES.md

- Byte 8 bit 0x08 as the "program running" flag
- Byte 4 as a mechanical coding pin including the CLEAN value
- The 60-second send pattern (12/24/24) and its consequence for live sensors
- 0xa3 returns 16 data bytes on the 656.55, contrary to longshot
