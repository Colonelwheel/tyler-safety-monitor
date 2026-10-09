# Optional facial gaming frame sharing

The camera remains owned by Tyler Safety Monitor. Facial inference runs in the
separate Facial Gaming Input app and connects to Simplecontroller's receiver.
Sharing is **off on every monitor launch** and never opens a second webcam.
The export path does not change camera resolution/FPS, safety ROI, pose settings,
personal calibration, warning simulations, audio, SMS, or the public website.

## One-pointer setup

1. Open **Camera** and wait for its live view. Keep calibration idle and leave
   feature replay before setup.
2. Press **Select Face Region**. Tap one corner around the face and then the
   opposite corner. There is no drag or simultaneous-key input. The white
   rectangle describes only the optional exported face crop.
3. Press **Enable Face Sharing**. The status names its pixel size. Selection
   alone never enables sharing. **Disable Face Sharing** stops it immediately.
4. In the facial app, use its non-output **Test** and **Calibrate** modes to
   compare mouth opening with eyebrow raising. Verify the usual camera view
   actually contains enough facial detail; small faces are never upscaled.

Existing exclusion masks are blacked out before export. The independent face
crop can differ from the pose inference ROI; neither control alters the other.
Review the exclusions in the normal monitor interface if they cover the face.
Pausing/restarting the camera, automatic camera reconnection, or changing the
safety scene stops sharing and clears the face crop. Select and enable again
after reviewing the live picture. The face region is memory-only for this launch
and is not included in **Save Settings**.

## Transport and bounds

An independent export thread reads the capture's immutable `latest_frame()` and
`snapshot()` references, not its process queues. It copies only the selected
crop, applies intersecting masks, and shrinks it if necessary to at most 640 ×
480 BGR. It never increases resolution. It polls at most 30 times per second,
skips duplicate sequences, and invalidates frames older than 250 ms. The facial
consumer independently caps inference (15 FPS by default).

Version 1 uses two shared-memory slots, a fixed 128-byte header and an aligned
64-bit revision seqlock. Allocation is 1,843,328 bytes, independent of consumer
speed. Windows x64 is the supported production runtime. There is no consumer
acknowledgement, consumer lock, recording, growing image queue or network feed.
Consumers get a detached BGR copy after header/payload consistency checks, with
capture monotonic time, sequence, camera generation, scene generation and a new
publisher-session identifier. They make at most three read attempts and expose
distinct ready/missing/busy/stale/paused/fault states.

The shared-memory name is `tsm_face_v1_` followed by a stable hash of the Windows
username; AppData redirection does not affect discovery. The client maps it with
`FILE_MAP_READ`, does not register resource-tracker ownership and never unlinks
it. Only the publisher owns cleanup. A second publisher refuses an existing name
and leaves it intact. Clients close paused/stale mappings so a restarted owner
can acquire its name. The feed is local to the Windows account/session; it is
not a permission boundary against other programs already running as that user.

## Verification and remaining live checks

Synthetic tests cover detached reads, existing-owner refusal, torn publication,
bounded allocation without a consumer, stopped/stale/missing feeds, fresh
publisher sessions, invalid frame metadata, crop-first masking, no upscaling,
camera faults/reconnections and stopping during a crop copy. Offscreen Qt tests
use fake camera/audio/tray adapters and single-pointer button/tap events; they
check unchanged safety geometry and explicit opt-in per launch.

Implementation verification: all 666 staged/existing synthetic tests passed in
35.29 seconds, including the 20-test exporter suite. The owned writer/reader probe used 640 × 480
generated patterns and checked every accepted pixel against its frame sequence.
No actual camera supplied these frames.

A separate real Face Landmarker CPU smoke run in the facial app's isolated
environment processed 30 generated blank crops correctly as no-face results.
Mean native call time was 3.892 ms, p95 4.600 ms, child working set 142.76 MiB,
first result after 2.640 seconds and graceful owned-child stop in 0.125 seconds.
Those figures measure the blank/no-face path, including the app's shared-feed
consumer; they do not establish costs or reliability when an actual face is
visible. The script is `integrations/monitor/scripts/native_blank_smoke.py` in the
facial application workspace, uses its own test feed, and opens no receiver.

No live camera view, facial-expression reliability, actual Xbox controller,
game compatibility, fatigue or combined gaming/safety-monitor benchmark has been
validated by these tests. Do the approved ordinary-posture expression comparison
and combined benchmark before treating this as a usable gameplay control.
Keep safety-monitor settings fixed; reduce or pause facial processing if it
degrades camera/inference cadence or game frame times. No caregiver involvement,
real SMS or new safety behavior is part of this feature.
