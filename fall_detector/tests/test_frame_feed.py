import struct
import time
from uuid import uuid4
import multiprocessing as mp

import numpy as np
import pytest

from tyler_safety_monitor.frame_feed import (
    HEADER, HEADER_BYTES, SIZE, SLOT_BYTES, SharedFramePublisher, SharedFrameReader,
)


@pytest.fixture
def feed():
    owner = SharedFramePublisher("face_test_" + uuid4().hex)
    reader = SharedFrameReader(owner.name, clock=lambda: 10.1)
    yield owner, reader
    reader.close()
    owner.close()


def publish(owner, value=4, seq=1):
    owner.publish(np.full((10, 20, 3), value, dtype=np.uint8), 10.0, seq, 2, 3)


def test_readonly_detached_copy_preserves_owner_frame_and_metadata(feed):
    owner, reader = feed
    publish(owner)
    packet = reader.read_latest()
    assert reader.status == "ready"
    assert packet.sequence == 1 and packet.camera_generation == 2 and packet.scene_generation == 3
    assert packet.captured_at == 10.0 and len(packet.session_id) == 32
    packet.image[:] = 99
    assert np.all(reader.read_latest().image == 4)
    reader.close()
    another = SharedFrameReader(owner.name, clock=lambda: 10.1)
    try:
        assert np.all(another.read_latest().image == 4)
    finally:
        another.close()


def test_missing_paused_stale_are_distinct_and_readers_release_mapping(feed):
    owner, reader = feed
    assert reader.read_latest() is None and reader.status == "paused"
    publish(owner)
    reader._clock = lambda: 10.251
    assert reader.read_latest() is None and reader.status == "stale"
    assert reader._mapping is None
    missing = SharedFrameReader("face_missing_" + uuid4().hex)
    assert missing.read_latest() is None and missing.status == "missing"


def test_reader_cannot_block_publisher_and_allocation_remains_bounded(feed):
    owner, reader = feed
    for sequence in range(200):
        publish(owner, seq=sequence)
    assert owner._shared.size == SIZE == HEADER_BYTES + 2 * SLOT_BYTES
    assert reader.read_latest().sequence == 199


def test_existing_feed_refused_without_unlink_or_mutation(feed):
    owner, reader = feed
    publish(owner)
    with pytest.raises(FileExistsError):
        SharedFramePublisher(owner.name)
    assert np.all(reader.read_latest().image == 4)


def test_seqlock_never_returns_busy_or_torn_frame(feed):
    owner, reader = feed
    publish(owner)
    owner._store_revision(owner._revision + 1)
    assert reader.read_latest() is None and reader.status == "busy"
    owner._store_revision(owner._revision)
    assert reader.read_latest() is not None
    original_read = reader._mapping.read
    changed = False
    def interrupted_read(offset, size):
        nonlocal changed
        raw = original_read(offset, size)
        if offset >= HEADER_BYTES and not changed:
            changed = True
            publish(owner, value=8, seq=2)
        return raw
    reader._mapping.read = interrupted_read
    packet = reader.read_latest()
    assert packet.sequence == 2 and np.all(packet.image == 8)


def test_restart_has_new_session_and_reader_does_not_own_cleanup():
    name = "face_restart_" + uuid4().hex
    owner = SharedFramePublisher(name)
    reader = SharedFrameReader(name, clock=lambda: 10.1)
    publish(owner)
    first = reader.read_latest()
    owner.close()
    assert reader.read_latest() is None and reader.status == "paused"
    restarted = SharedFramePublisher(name)
    try:
        publish(restarted)
        assert reader.read_latest().session_id != first.session_id
    finally:
        reader.close()
        restarted.close()


@pytest.mark.parametrize("image", [np.zeros((481, 1, 3), np.uint8), np.zeros((1, 641, 3), np.uint8), np.zeros((1, 1)), np.zeros((1, 1, 3), np.float32)])
def test_publisher_rejects_oversize_or_invalid_frames(feed, image):
    owner, reader = feed
    with pytest.raises(ValueError):
        owner.publish(image, 10.0, 1, 2, 3)
    assert reader.read_latest() is None and reader.status == "paused"


def test_invalid_wire_geometry_fails_closed(feed):
    owner, reader = feed
    publish(owner)
    fields = list(HEADER.unpack(bytes(owner._shared.buf[:HEADER.size])))
    fields[9] = 100000
    owner._shared.buf[:HEADER.size] = HEADER.pack(*fields)
    assert reader.read_latest() is None and reader.status == "fault"


def _probe_reader(name, result, ready):
    reader = SharedFrameReader(name, stale_after=.250)
    checked = 0
    consistent = True
    ready.set()
    deadline = time.monotonic() + 1.0
    try:
        while time.monotonic() < deadline:
            packet = reader.read_latest()
            if packet is not None:
                checked += 1
                consistent = consistent and bool(np.all(packet.image == packet.sequence % 256))
        result.put((checked, consistent))
    finally:
        reader.close()


def test_generated_frames_across_separate_process_are_consistent_without_consumer_lock():
    name = "face_process_" + uuid4().hex
    context = mp.get_context("spawn")
    result = context.Queue(maxsize=1)
    ready = context.Event()
    owner = SharedFramePublisher(name)
    worker = context.Process(target=_probe_reader, args=(name, result, ready))
    worker.start()
    try:
        assert ready.wait(5), "synthetic reader failed to initialize"
        until = time.monotonic() + 1.2
        sequence = 0
        while time.monotonic() < until:
            sequence += 1
            owner.publish(np.full((480, 640, 3), sequence % 256, np.uint8),
                          time.monotonic(), sequence, 4, 7)
        worker.join(timeout=3)
        assert worker.exitcode == 0
        checked, consistent = result.get(timeout=1)
        assert checked > 10 and consistent
        assert owner._shared.size == SIZE
    finally:
        if worker.is_alive():
            worker.terminate()  # only this test's owned synthetic child
            worker.join(timeout=2)
        worker.close()
        owner.close()
        result.close()
