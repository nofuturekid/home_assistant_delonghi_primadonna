import asyncio
import logging
import os
import sys
import time

from bleak.exc import BleakError

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "custom_components",
        )
    )
)

import delonghi_primadonna.device as device_module  # noqa: E402
from delonghi_primadonna.const import BYTES_STATISTICS_COMMAND  # noqa: E402
from delonghi_primadonna.device import DelongiPrimadonna  # noqa: E402
from delonghi_primadonna.device_tracker import \
    DelongiPrimadonnaDeviceTracker  # noqa: E402

CONFIG = {
    "mac": "00:11:22:33:44:55",
    "model": "TEST",
    "name": "TEST",
}


def make_device(hass=None):
    return DelongiPrimadonna(CONFIG, hass)


class FakeHass:
    def __init__(self):
        self.created_tasks = []
        self.background_tasks = []

    def async_create_task(self, coro):
        task = asyncio.create_task(coro)
        self.created_tasks.append(task)
        return task

    def async_create_background_task(self, coro, _name):
        task = asyncio.create_task(coro)
        self.background_tasks.append(task)
        return task


class FakeConnectClient:
    def __init__(
        self,
        *,
        notify_error=None,
        block_notify=False,
    ):
        self.is_connected = True
        self.notify_error = notify_error
        self.block_notify = block_notify
        self.notify_started = asyncio.Event()
        self.notify_release = asyncio.Event()
        self.start_notify_calls = 0
        self.disconnect_calls = 0

    async def start_notify(self, _characteristic, _callback):
        self.start_notify_calls += 1
        self.notify_started.set()

        if self.notify_error is not None:
            raise self.notify_error

        if self.block_notify:
            await self.notify_release.wait()

    async def disconnect(self):
        self.disconnect_calls += 1
        self.is_connected = False


class FailingWriteClient:
    is_connected = True

    def __init__(self):
        self.disconnect_calls = 0

    async def write_gatt_char(
        self,
        _characteristic,
        _message,
    ):
        raise BleakError("write failed")

    async def disconnect(self):
        self.disconnect_calls += 1
        self.is_connected = False


async def run_with_fake_connection(device, client):
    original_lookup = (
        device_module.bluetooth.async_ble_device_from_address
    )
    original_establish = device_module.establish_connection

    fake_ble_device = object()

    def fake_lookup(_hass, _mac, connectable):
        assert connectable is True
        return fake_ble_device

    async def fake_establish(
        _client_class,
        ble_device,
        _name,
        max_attempts,
    ):
        assert ble_device is fake_ble_device
        assert max_attempts == 3
        return client

    device_module.bluetooth.async_ble_device_from_address = (
        fake_lookup
    )
    device_module.establish_connection = fake_establish

    try:
        await device._connect()
    finally:
        device_module.bluetooth.async_ble_device_from_address = (
            original_lookup
        )
        device_module.establish_connection = original_establish


async def test_connect_success():
    device = make_device()
    client = FakeConnectClient()

    await run_with_fake_connection(device, client)

    assert device._client is client
    assert device.connected is True
    assert client.start_notify_calls == 1
    assert client.disconnect_calls == 0
    assert device._connecting is False


async def test_connect_clears_receive_buffer_before_notifications():
    device = make_device()
    device._rx_buffer.extend(
        b"\\xd0\\x41\\xa2\\x0f\\x00"
    )
    client = FakeConnectClient()

    observed_buffer = None
    original_start_notify = client.start_notify

    async def inspecting_start_notify(
        characteristic,
        callback,
    ):
        nonlocal observed_buffer
        observed_buffer = bytes(device._rx_buffer)
        await original_start_notify(
            characteristic,
            callback,
        )

    client.start_notify = inspecting_start_notify

    await run_with_fake_connection(device, client)

    assert observed_buffer == b""
    assert device._rx_buffer == bytearray()


RX_TEST_PACKET = bytes.fromhex(
    "d0 41 a2 0f 00 64 2d 34 3b 42 49 50 57 5e 65 6c "
    "73 7a 81 88 8f 96 9d a4 ab b2 b9 c0 c7 ce d5 dc "
    "e3 ea f1 f8 ff 06 0d 14 1b 22 29 30 37 3e 45 4c "
    "53 5a 61 68 6f 76 7d 84 8b 92 99 a0 a7 ae b5 bc "
    "05 97"
)


async def test_receive_buffer_reassembles_fragmented_packet():
    device = make_device()
    handled_packets = []

    async def capture_packet(_sender, packet):
        handled_packets.append(bytes(packet))

    device._handle_data = capture_packet

    await device._process_raw_data(None, RX_TEST_PACKET[:20])

    assert handled_packets == []
    assert device._rx_buffer == bytearray(RX_TEST_PACKET[:20])

    await device._process_raw_data(None, RX_TEST_PACKET[20:])

    assert handled_packets == [RX_TEST_PACKET]
    assert device._rx_buffer == bytearray()


async def test_receive_buffer_discards_invalid_crc_packet():
    device = make_device()
    handled_packets = []

    assert device._has_valid_crc(RX_TEST_PACKET)

    corrupted_packet = bytearray(RX_TEST_PACKET)
    corrupted_packet[-1] ^= 0x01
    corrupted_packet = bytes(corrupted_packet)

    assert not device._has_valid_crc(corrupted_packet)

    device._expected_statistics_start = 100
    device._response_event = asyncio.Event()

    async def no_event(_value):
        return None

    device._event_trigger = no_event

    original_handle_data = device._handle_data

    async def capture_and_handle(sender, packet):
        handled_packets.append(bytes(packet))
        await original_handle_data(sender, packet)

    device._handle_data = capture_and_handle

    await device._process_raw_data(None, corrupted_packet)

    assert handled_packets == []
    assert not device._response_event.is_set()
    assert not device.statistics
    assert device._rx_buffer == bytearray()


async def test_receive_buffer_recovers_from_restarted_frame():
    device = make_device()
    handled_packets = []

    async def capture_packet(_sender, packet):
        handled_packets.append(bytes(packet))

    device._handle_data = capture_packet

    await device._process_raw_data(None, RX_TEST_PACKET[:20])

    assert handled_packets == []

    # Reproduce the live failure: after a 20-byte partial packet, the
    # device restarts transmission from the beginning of the same frame.
    await device._process_raw_data(None, RX_TEST_PACKET)

    assert handled_packets == [RX_TEST_PACKET]
    assert device._rx_buffer == bytearray()


async def test_notify_failure_disconnects_client():
    device = make_device()
    client = FakeConnectClient(
        notify_error=BleakError("notify failed")
    )

    try:
        await run_with_fake_connection(device, client)
    except BleakError:
        pass
    else:
        raise AssertionError(
            "_connect did not propagate start_notify failure"
        )

    assert client.disconnect_calls == 1
    assert device._client is None
    assert device.connected is False
    assert device._connecting is False


async def test_connect_cancellation_disconnects_client():
    device = make_device()
    client = FakeConnectClient(block_notify=True)

    original_lookup = (
        device_module.bluetooth.async_ble_device_from_address
    )
    original_establish = device_module.establish_connection

    fake_ble_device = object()

    def fake_lookup(_hass, _mac, connectable):
        assert connectable is True
        return fake_ble_device

    async def fake_establish(
        _client_class,
        ble_device,
        _name,
        max_attempts,
    ):
        assert ble_device is fake_ble_device
        assert max_attempts == 3
        return client

    device_module.bluetooth.async_ble_device_from_address = (
        fake_lookup
    )
    device_module.establish_connection = fake_establish

    task = asyncio.create_task(device._connect())

    try:
        await client.notify_started.wait()

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError(
                "_connect did not propagate cancellation"
            )
    finally:
        device_module.bluetooth.async_ble_device_from_address = (
            original_lookup
        )
        device_module.establish_connection = original_establish

    assert client.disconnect_calls == 1
    assert device._client is None
    assert device._connecting is False


async def test_write_bleak_error_disconnects_client():
    device = make_device()
    client = FailingWriteClient()
    device._client = client

    async def fake_connect():
        return None

    device._connect = fake_connect

    original_sleep = device_module.asyncio.sleep

    async def no_sleep(_delay):
        return None

    device_module.asyncio.sleep = no_sleep

    try:
        result = await device.send_command(
            list(BYTES_STATISTICS_COMMAND),
            retries=1,
        )
    finally:
        device_module.asyncio.sleep = original_sleep

    assert result is False
    assert client.disconnect_calls == 1
    assert device._client is None
    assert device.connected is False


async def test_initialization_task_is_cancelled_and_awaited():
    device = make_device()

    started = asyncio.Event()
    cleaned_up = asyncio.Event()

    async def initialization():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned_up.set()

    task = asyncio.create_task(initialization())
    device.set_initialization_task(task)

    await started.wait()
    await device.cancel_initialization()

    assert device._initialization_task is None
    assert task.cancelled()
    assert cleaned_up.is_set()


async def test_get_device_name_propagates_cancellation():
    device = make_device()

    async def cancelled_connect():
        raise asyncio.CancelledError

    device._connect = cancelled_connect

    try:
        await device.get_device_name()
    except asyncio.CancelledError:
        pass
    else:
        raise AssertionError(
            "get_device_name swallowed cancellation"
        )

    assert device.connected is False


class FakeTrackerDevice:
    def __init__(self):
        self.calls = 0
        self.started = asyncio.Event()

    async def get_device_name(self):
        self.calls += 1
        self.started.set()
        await asyncio.Event().wait()


async def test_tracker_deduplicates_and_cancels_update():
    hass = FakeHass()
    fake_device = FakeTrackerDevice()

    tracker = DelongiPrimadonnaDeviceTracker.__new__(
        DelongiPrimadonnaDeviceTracker
    )
    tracker.hass = hass
    tracker.device = fake_device
    tracker._device_name_task = None

    await tracker.async_update()
    first_task = tracker._device_name_task

    await tracker.async_update()
    second_task = tracker._device_name_task

    await fake_device.started.wait()

    assert first_task is second_task
    assert fake_device.calls == 1
    assert hass.created_tasks == []
    assert len(hass.background_tasks) == 1

    await tracker.async_will_remove_from_hass()

    assert tracker._device_name_task is None
    assert first_task.cancelled()


async def test_statistics_task_deduplicates_and_cancels():
    hass = FakeHass()
    device = make_device(hass)

    calls = 0
    started = asyncio.Event()

    async def statistics_update():
        nonlocal calls
        calls += 1
        started.set()
        await asyncio.Event().wait()

    device.update_statistics = statistics_update
    device._last_stats_request = 0.0

    device.schedule_statistics_update()
    first_task = device._statistics_task

    device.schedule_statistics_update()
    second_task = device._statistics_task

    await started.wait()

    assert first_task is second_task
    assert calls == 1
    assert hass.created_tasks == []
    assert len(hass.background_tasks) == 1

    await device.cancel_statistics_update()

    assert device._statistics_task is None
    assert first_task.cancelled()


async def test_failed_statistics_attempt_is_throttled():
    hass = FakeHass()
    device = make_device(hass)
    calls = []

    async def failed_statistics(start_index, count):
        calls.append((start_index, count))
        return False

    device.get_statistics = failed_statistics
    device._last_stats_request = 0.0

    before = time.monotonic()
    await device.update_statistics()
    after = time.monotonic()

    assert calls == [(100, 10)]
    assert before <= device._last_stats_request <= after

    device.schedule_statistics_update()

    assert device._statistics_task is None
    assert hass.background_tasks == []


async def test_statistics_update_exception_is_contained_and_reschedulable():
    hass = FakeHass()
    device = make_device(hass)
    calls = 0

    async def failing_statistics_update():
        nonlocal calls
        calls += 1
        raise RuntimeError("statistics failed")

    device.update_statistics = failing_statistics_update
    device._last_stats_request = 0.0

    device.schedule_statistics_update()
    first_task = device._statistics_task

    assert first_task is not None

    await first_task

    assert first_task.done()
    assert not first_task.cancelled()
    assert device._statistics_task is first_task
    assert calls == 1

    device.schedule_statistics_update()
    second_task = device._statistics_task

    assert second_task is not None
    assert second_task is not first_task

    await second_task

    assert second_task.done()
    assert not second_task.cancelled()
    assert device._statistics_task is second_task
    assert calls == 2
    assert len(hass.background_tasks) == 2


async def test_statistics_schedule_respects_throttle():
    hass = FakeHass()
    device = make_device(hass)

    device._last_stats_request = time.monotonic()

    device.schedule_statistics_update()

    assert device._statistics_task is None
    assert hass.created_tasks == []


async def test_unanswered_profile_request_backs_off():
    """A machine that never answers 0xA4 must not be re-asked every cycle.

    update_settings() retries _request_profile_names() while
    _profiles_received is False. That flag is only set when a profile
    response actually parses, so a machine that ignores the command
    causes an unbounded retry: two commands, ten seconds of blocked
    device lock each, once per settings cycle, forever.
    """
    device = make_device()
    profile_calls = []

    async def never_answered():
        profile_calls.append(time.monotonic())

    async def noop_send(message, retries=3):
        return True

    saved_params = device_module.READABLE_PARAMETERS
    device_module.READABLE_PARAMETERS = []
    try:
        device._request_profile_names = never_answered
        device.send_command = noop_send
        device.sync_time = False
        device._profiles_received = False

        cycles = 5
        for _ in range(cycles):
            # Each iteration stands for a fresh settings cycle.
            device._last_switches_request = 0.0
            await device.update_settings()
    finally:
        device_module.READABLE_PARAMETERS = saved_params

    assert len(profile_calls) < cycles, (
        "profile request was repeated on every cycle "
        f"({len(profile_calls)}/{cycles}) - no backoff"
    )


async def test_repeated_profile_failure_is_reported_once():
    """An unchanging failure belongs in the log once, not on every retry.

    Backing off reduced how often the profile request is repeated, but a
    condition that does not change should be reported when it starts and
    when it ends - not once per attempt forever.
    """
    device = make_device()
    warnings = []

    class _Collect(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING:
                warnings.append(record.getMessage())

    async def never_answered():
        return None

    async def noop_send(message, retries=3, log_timeout=True):
        return False

    handler = _Collect()
    device_module._LOGGER.addHandler(handler)
    saved_params = device_module.READABLE_PARAMETERS
    device_module.READABLE_PARAMETERS = []
    try:
        device._request_profile_names = never_answered
        device.send_command = noop_send
        device.sync_time = False
        device._profiles_received = False

        for _ in range(4):
            # Force the retry every cycle: this tests the reporting, not
            # the backoff, which has its own test.
            device._last_switches_request = 0.0
            device._profiles_retry_at = 0.0
            await device.update_settings()
    finally:
        device_module.READABLE_PARAMETERS = saved_params
        device_module._LOGGER.removeHandler(handler)

    assert len(warnings) == 1, (
        "an unchanging failure should be reported exactly once, got "
        f"{len(warnings)}: {warnings}"
    )


async def test_command_names_are_human_readable():
    """A timeout line must say what failed, not only dump bytes.

    "Timeout waiting for response to command: b'0d 07 e2 f0 12 06 97 ae'"
    requires reverse-engineering the protocol to act on. The command type
    lives in byte 2 and has a name.
    """
    describe = device_module.describe_command

    # 0xE2 with hour/minute: the clock sync
    assert describe([0x0d, 0x07, 0xE2, 0xF0, 0x12, 0x06, 0x97, 0xae]) == \
        'clock'
    assert describe(list(BYTES_STATISTICS_COMMAND)) == 'statistics'
    assert describe([0x0d, 0x07, 0xA4, 0xF0]) == 'profile names'
    assert describe([0x0d, 0x07, 0x95, 0x0F]) == 'read setting'

    # Unknown or malformed commands still identify themselves
    assert describe([0x0d, 0x07, 0x42]) == '0x42'
    assert describe([0x0d]) == 'unknown'


class _CollectWarnings(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        if record.levelno >= logging.WARNING:
            self.messages.append(record.getMessage())


async def _connect_with(device, lookup, establish=None):
    """Drive get_device_name() with a stubbed BLE lookup, collecting warnings."""
    handler = _CollectWarnings()
    original_lookup = device_module.bluetooth.async_ble_device_from_address
    original_establish = device_module.establish_connection
    device_module._LOGGER.addHandler(handler)
    device_module.bluetooth.async_ble_device_from_address = lookup
    if establish is not None:
        device_module.establish_connection = establish
    try:
        await device.get_device_name()
    finally:
        device_module.bluetooth.async_ble_device_from_address = original_lookup
        device_module.establish_connection = original_establish
        device_module._LOGGER.removeHandler(handler)
    return handler.messages


async def test_machine_out_of_range_is_not_a_warning():
    """A machine that is switched off is not a fault.

    _connect() raises when HA has no connectable route to the MAC, which
    is exactly what an appliance that is off looks like. It surfaced as
    two WARNING lines per attempt: _connect() logged and re-raised, and
    the caller logged the same exception again.
    """
    device = make_device()

    warnings = await _connect_with(device, lambda _h, _m, connectable: None)

    assert device.connected is False
    assert warnings == [], (
        f"an unreachable machine should not warn, got: {warnings}"
    )


async def test_connect_failure_while_visible_warns_once():
    """A machine in range that will not connect is worth exactly one line."""
    device = make_device()
    ble_device = object()

    async def failing_establish(_cls, _dev, _name, max_attempts):
        raise BleakError("connect failed")

    warnings = await _connect_with(
        device,
        lambda _h, _m, connectable: ble_device,
        establish=failing_establish,
    )

    assert device.connected is False
    assert len(warnings) == 1, (
        f"expected one warning for a real failure, got {len(warnings)}: "
        f"{warnings}"
    )


async def run_tests():
    await test_connect_success()
    await test_connect_clears_receive_buffer_before_notifications()
    await test_receive_buffer_reassembles_fragmented_packet()
    await test_receive_buffer_discards_invalid_crc_packet()
    await test_receive_buffer_recovers_from_restarted_frame()
    await test_notify_failure_disconnects_client()
    await test_connect_cancellation_disconnects_client()
    await test_write_bleak_error_disconnects_client()

    await test_initialization_task_is_cancelled_and_awaited()
    await test_get_device_name_propagates_cancellation()
    await test_tracker_deduplicates_and_cancels_update()

    await test_statistics_task_deduplicates_and_cancels()
    await test_failed_statistics_attempt_is_throttled()
    await test_statistics_update_exception_is_contained_and_reschedulable()
    await test_statistics_schedule_respects_throttle()
    await test_unanswered_profile_request_backs_off()
    await test_repeated_profile_failure_is_reported_once()
    await test_command_names_are_human_readable()
    await test_machine_out_of_range_is_not_a_warning()
    await test_connect_failure_while_visible_warns_once()

    print(
        "[SUCCESS] BLE lifecycle regressions "
        "for commits 1-3 verified."
    )


if __name__ == "__main__":
    asyncio.run(run_tests())
