import asyncio
import os
import sys

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "custom_components",
        )
    )
)

from delonghi_primadonna.binary_sensor import \
    DelongiPrimadonnaEnabledSensor  # noqa: E402
from delonghi_primadonna.device import DelongiPrimadonna  # noqa: E402

CONFIG = {
    "mac": "00:11:22:33:44:55",
    "model": "TEST",
    "name": "TEST",
}


def make_device():
    return DelongiPrimadonna(CONFIG, None)


class _RestoredState:
    def __init__(self, state):
        self.state = state


async def test_enabled_sensor_does_not_write_back_to_the_device():
    """A sensor reports state; it must not set it.

    async_added_to_hass() wrote Home Assistant's own remembered value
    into device.switches.is_on. After a restart that claimed the machine
    was on or off before a single frame had arrived - and a False->True
    flip also triggers the profile fetch, for a wake-up that never
    happened.
    """
    device = make_device()
    sensor = DelongiPrimadonnaEnabledSensor(device, None)

    async def last_state():
        return _RestoredState('on')

    sensor.async_get_last_state = last_state
    device.switches.is_on = False

    await sensor.async_added_to_hass()

    assert device.switches.is_on is False, (
        "the sensor wrote Home Assistant's remembered value into the device"
    )


async def test_enabled_sensor_follows_the_device():
    """It reports what the machine says, and nothing else."""
    device = make_device()
    sensor = DelongiPrimadonnaEnabledSensor(device, None)

    device.switches.is_on = True
    assert sensor.is_on is True

    device.switches.is_on = False
    assert sensor.is_on is False


async def run_tests():
    await test_enabled_sensor_does_not_write_back_to_the_device()
    await test_enabled_sensor_follows_the_device()

    print("[SUCCESS] Entity behaviour verified.")


if __name__ == "__main__":
    asyncio.run(run_tests())
