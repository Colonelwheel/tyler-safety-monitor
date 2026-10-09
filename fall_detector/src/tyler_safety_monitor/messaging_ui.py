"""Large controls for a fake in-memory transport; no account or recipient entry."""
from dataclasses import replace

from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from .simulation_messaging import FALL_MESSAGE, CHOKING_MESSAGE


class MessagingControls(QWidget):
    def __init__(self, session, snapshot, position, receive_reply, parent=None):
        super().__init__(parent)
        self.session, self.snapshot, self.position = session, snapshot, position
        self.receive_reply = receive_reply
        self._last_reply = None
        self._session_id = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.status = QLabel()
        self.status.setAccessibleName("Simulated messaging status")
        self.preview = QLabel()
        self.preview.setAccessibleName("Simulated message preview")
        self.note = QLabel("SIMULATION ONLY. No text is sent. Every scheduled attempt counts toward ten, including failure/unknown. Outcome settings apply to future attempts; no immediate retry.")
        for label in (self.status, self.preview, self.note):
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            layout.addWidget(label)
        self.outcome = QComboBox()
        self.outcome.setAccessibleName("Fake outcome for future message attempts")
        for status in ("delivered", "accepted", "sent", "delayed", "rejected", "failed", "undelivered", "unknown"):
            self.outcome.addItem("Fake " + status, status)
        self.outcome.setMinimumHeight(60)
        self.outcome.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.outcome)
        self.delay = QDoubleSpinBox()
        self.delay.setAccessibleName("Fake delivery delay in simulation seconds")
        self.delay.setRange(.1, 600)
        self.delay.setValue(5)
        self.delay.setDecimals(1)
        self.delay.setSuffix(" seconds for Fake delayed")
        self.delay.setMinimumHeight(60)
        self.delay.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.delay)
        self.outcome.currentIndexChanged.connect(self.configure)
        self.delay.valueChanged.connect(self.configure)
        self.reply_type = QComboBox()
        self.reply_type.setAccessibleName("Fake caregiver reply case")
        for label, case in (
            ("Valid caregiver reply", "valid"), ("Wrong sender", "sender"),
            ("Wrong recipient", "recipient"), ("Reply before episode", "old"),
            ("Future reply", "future"), ("Duplicate previous reply", "duplicate"),
            ("Prior-session reply", "session"),
        ):
            self.reply_type.addItem(label, case)
        self.reply_type.setMinimumHeight(60)
        self.reply_type.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.reply_type)
        self.reply_button = QPushButton("Simulate Caregiver\nReply")
        self.reply_button.setAccessibleName("Simulate Caregiver Reply")
        self.reply_button.setMinimumHeight(60)
        self.reply_button.clicked.connect(self.send_reply)
        layout.addWidget(self.reply_button)
        self.reply_status = QLabel("Reply time must be after this episode began; pause freezes simulation time.")
        self.reply_status.setWordWrap(True)
        self.reply_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.reply_status)

    def configure(self, *_):
        self.session().set_outcome(self.outcome.currentData(),
                                   self.delay.value() if self.outcome.currentData() == "delayed" else 0.)

    def reset(self):
        self._last_reply = None
        self._session_id = self.session().session_id
        self.reply_status.setText("New simulation session; prior replies/results cannot acknowledge it.")
        self.configure()

    def send_reply(self):
        session = self.session()
        if self._session_id != session.session_id:
            self.reset()
        now = self.position()
        snapshot = self.snapshot()
        reply = session.make_reply(now)
        case = self.reply_type.currentData()
        if case == "sender":
            reply = replace(reply, sender="synthetic:other")
        elif case == "recipient":
            reply = replace(reply, recipient="synthetic:other")
        elif case == "old":
            reply = replace(reply, created=snapshot.episode_started or 0.)
        elif case == "future":
            reply = replace(reply, created=now + 1.)
        elif case == "session":
            reply = replace(reply, session_id="prior-simulation-session")
        elif case == "duplicate":
            if self._last_reply is None:
                self.reply_status.setText("No previous reply in this session to duplicate.")
                return
            reply = self._last_reply
        if self.receive_reply(reply):
            self._last_reply = reply
            self.reply_status.setText("Valid simulated reply acknowledged. Choking still requires manual Cancel/Resolve.")
        else:
            self.reply_status.setText("Reply ignored: check enabled session, sender, recipient, time and unique reply ID.")

    def render(self, enabled=True):
        session, snapshot = self.session(), self.snapshot()
        if self._session_id != session.session_id:
            self.reset()
        summary = session.summary(snapshot.episode_id)
        unavailable = bool(summary.error or summary.last_status in {
            "rejected", "failed", "undelivered", "unknown",
        })
        self.status.setText(
            f"SIMULATED MESSAGING • episode {snapshot.episode_id}\n"
            f"Intent slots {snapshot.message_count} / 10 • Attempts {summary.attempted}\n"
            f"Fake accepted {summary.accepted} • delivered {summary.delivered} • failures {summary.failed}\n"
            f"Pending {summary.pending} • unknown {summary.unknown} • last {summary.last_status}"
            + ("\nSimulated messaging unavailable." if unavailable else "")
            + (f"\n{summary.error}" if summary.error else "")
        )
        body = CHOKING_MESSAGE if snapshot.choking else FALL_MESSAGE
        current = [record for record in session.records if record.episode_id == snapshot.episode_id]
        self.preview.setText(current[-1].preview if current else
                             "SIMULATION ONLY • Message preview:\n" + body)
        self.reply_button.setEnabled(enabled)
