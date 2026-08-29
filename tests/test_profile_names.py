"""Profile names must survive any script the machine allows."""

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

from delonghi_primadonna.device import DelongiPrimadonna  # noqa: E402

CONFIG = {
    "mac": "00:11:22:33:44:55",
    "model": "TEST",
    "name": "TEST",
}

NAME_SIZE = 20

# What follows the name area in a real reply: monitor/statistics bytes.
TRAILING = bytes.fromhex("d0127 50fb4b5b6b7b8".replace(" ", "")) + b"\xff" * 24


def response(names, start=1):
    """Build an 0xa4 reply carrying the given names."""
    out = bytearray([0xD0, 0x12, 0xA4, 0x0F])
    for name in names:
        encoded = name.encode("utf-16-be")[:NAME_SIZE]
        out += encoded + b"\x00" * (NAME_SIZE - len(encoded)) + b"\x00"
    return bytes(out) + TRAILING


def parse(names, start=1, count=None):
    device = DelongiPrimadonna(CONFIG, None)
    device._profile_request_start = start
    device._profile_request_count = count if count else len(names)
    return device._parse_profile_response(list(response(names, start)))


async def test_latin_names():
    assert parse(["Nicole", "Thomas", "Gast"]) == {
        1: "Nicole", 2: "Thomas", 3: "Gast",
    }


async def test_accented_names_are_not_truncated():
    """The character allow-list cut Zoé to Zo and François to Fran."""
    assert parse(["Zoé", "François", "José"]) == {
        1: "Zoé", 2: "François", 3: "José",
    }


async def test_non_latin_names_are_not_lost():
    """Cyrillic and Chinese names came out empty and ended the walk."""
    assert parse(["Сергей", "Тест1"]) == {1: "Сергей", 2: "Тест1"}
    assert parse(["李伟", "测试"]) == {1: "李伟", 2: "测试"}


async def test_trailing_payload_is_not_read_as_a_name():
    """Only the requested slots belong to the name area."""
    assert parse(["Nicole"], count=1) == {1: "Nicole"}


async def test_an_empty_slot_does_not_end_the_walk():
    assert parse(["Nicole", "", "Thomas"]) == {1: "Nicole", 3: "Thomas"}


async def test_numbering_follows_the_requested_range():
    assert parse(["Vier", "Fünf", "Sechs"], start=4) == {
        4: "Vier", 5: "Fünf", 6: "Sechs",
    }


async def run_tests():
    await test_latin_names()
    await test_accented_names_are_not_truncated()
    await test_non_latin_names_are_not_lost()
    await test_trailing_payload_is_not_read_as_a_name()
    await test_an_empty_slot_does_not_end_the_walk()
    await test_numbering_follows_the_requested_range()
    print("[SUCCESS] Profile name parsing verified.")


if __name__ == "__main__":
    asyncio.run(run_tests())
