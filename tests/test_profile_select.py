"""The profile select must show the machine's answer as soon as it comes."""

import asyncio
import os
import sys
from binascii import unhexlify

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "custom_components",
        )
    )
)

from delonghi_primadonna.device import DelongiPrimadonna  # noqa: E402
from delonghi_primadonna.select import ProfileSelect  # noqa: E402

CONFIG = {
    "mac": "00:11:22:33:44:55",
    "model": "TEST",
    "name": "TEST",
}

# Captured 2026-10-17 on an ECAM 656.55.MS: reply to "select profile 1".
REPLY_PROFILE_1 = unhexlify("d007a9f001003b3c")


class FakeHass:
    def __init__(self):
        self.tasks = []

    def async_create_task(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task


class AnsweringClient:
    is_connected = True

    def __init__(self, device, reply):
        self._device = device
        self._reply = reply

    async def write_gatt_char(self, _characteristic, _message):
        await self._device._handle_data(None, self._reply)


async def no_connect():
    return None


async def no_event(_value):
    return None


async def test_select_state_is_written_when_the_machine_answers():
    """Switching back to an earlier profile must not show the old one.

    Once a profile has been confirmed, current_option follows the
    machine's confirmed profile id. The 0xA9 reply arrives ~270 ms after
    the command, but nothing wrote the entity state then, so after
    switching Thomas -> Nicole the select kept showing "Thomas" until the
    next poll, ~16 s later (seen 2026-10-17).
    """
    hass = FakeHass()
    device = DelongiPrimadonna(CONFIG, hass)
    device._profiles = {1: "Nicole", 2: "Thomas"}
    device.profiles = list(device._profiles.values())
    device.active_profile_id = 2
    device._client = AnsweringClient(device, REPLY_PROFILE_1)
    device._connect = no_connect
    device._event_trigger = no_event

    select = ProfileSelect(device, hass)
    written = []
    select.async_write_ha_state = lambda: written.append(
        select.current_option
    )

    await select.async_select_option("Nicole")
    await asyncio.gather(*hass.tasks)
    await asyncio.sleep(0)

    assert device.active_profile_id == 1
    assert written and written[-1] == "Nicole", written


async def run_tests():
    await test_select_state_is_written_when_the_machine_answers()
    print("[SUCCESS] Profile select verified.")


if __name__ == "__main__":
    asyncio.run(run_tests())
