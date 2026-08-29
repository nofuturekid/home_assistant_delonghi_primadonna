"""Every status value must be a key the translations actually carry."""

import asyncio
import json
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

from delonghi_primadonna.const import DEVICE_STATUS  # noqa: E402
from delonghi_primadonna.const import MACHINE_STATUS  # noqa: E402

STRINGS = os.path.join(
    os.path.dirname(__file__),
    "..",
    "custom_components",
    "delonghi_primadonna",
    "strings.json",
)


def translation_keys():
    with open(STRINGS, encoding="utf-8") as handle:
        data = json.load(handle)
    return set(data["entity"]["sensor"]["device_status"]["state"])


async def test_alarm_values_are_translation_keys():
    """DEVICE_STATUS held English display text, which never matched.

    The sensor assigns these straight to its state, and Home Assistant
    looks the state up against the keys in strings.json. "Empty water
    tank" is not "empty_water_tank", so no alarm was ever translated.
    """
    keys = translation_keys()
    missing = sorted(v for v in DEVICE_STATUS.values() if v not in keys)

    assert not missing, f"no translation for: {missing}"


async def test_machine_values_are_translation_keys():
    keys = translation_keys()
    missing = sorted(v for v in MACHINE_STATUS.values() if v not in keys)

    assert not missing, f"no translation for: {missing}"


async def run_tests():
    await test_alarm_values_are_translation_keys()
    await test_machine_values_are_translation_keys()
    print("[SUCCESS] Status translation keys verified.")


if __name__ == "__main__":
    asyncio.run(run_tests())
