"""Manual test sound only. Never changes Windows output volume or mute."""

from __future__ import annotations

import math
import struct

from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices


class TestSound:
    __test__ = False

    def __init__(self) -> None:
        self.sink = None
        self.buffer = None

    def stop(self) -> None:
        if self.sink is not None:
            self.sink.stop()
            self.sink.deleteLater()
            self.sink = None
        if self.buffer is not None:
            self.buffer.close()
            self.buffer.deleteLater()
            self.buffer = None

    def play(self, volume: float) -> None:
        if not math.isfinite(volume) or not 0 <= volume <= 1:
            raise ValueError("test volume must lie between zero and one")
        self.stop()
        device = QMediaDevices.defaultAudioOutput()
        if device.isNull():
            raise RuntimeError("No active Windows audio output")
        audio_format = QAudioFormat()
        audio_format.setSampleRate(48000)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(audio_format):
            raise RuntimeError("Active output does not support the test sound format")
        samples = 24000
        pcm = bytearray()
        for index in range(samples):
            # Smooth edges avoid clicks; amplitude is controlled at app level.
            envelope = min(1.0, index / 480, (samples - index) / 480)
            value = int(12000 * envelope * math.sin(2 * math.pi * 660 * index / 48000))
            pcm.extend(struct.pack("<h", value))
        self.buffer = QBuffer()
        self.buffer.setData(QByteArray(bytes(pcm)))
        self.buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.sink = QAudioSink(device, audio_format)
        self.sink.setVolume(float(volume))
        self.sink.start(self.buffer)
