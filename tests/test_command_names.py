"""A timeout should say which command failed."""

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

from delonghi_primadonna.const import BYTES_POWER  # noqa: E402
from delonghi_primadonna.device import describe_command  # noqa: E402


async def test_known_commands_are_named():
    assert describe_command(BYTES_POWER) == "power"
    assert describe_command([0x0D, 0x07, 0xA4]) == "profile names"
    assert describe_command([0x0D, 0x07, 0x95]) == "read setting"


async def test_unknown_command_falls_back_to_its_type_byte():
    assert describe_command([0x0D, 0x07, 0x5A]) == "0x5a"


async def test_short_message_does_not_raise():
    assert describe_command([0x0D]) == "unknown"
    assert describe_command([]) == "unknown"


async def run_tests():
    await test_known_commands_are_named()
    await test_unknown_command_falls_back_to_its_type_byte()
    await test_short_message_does_not_raise()
    print("[SUCCESS] Command naming verified.")


if __name__ == "__main__":
    asyncio.run(run_tests())
