#!/usr/bin/env python3
"""
System Monitor Node
-------------------
Subscribes to ALL main topics and prints a live status table to the
terminal every second.  Tracks:
  - Whether each topic is alive (last message age)
  - Detection count and object labels from the latest frame
  - Latest depth values
  - Dangerous object flags
  - Latest security events and alerts
  - Rolling event/alert counters for the session
"""

import time
from collections import deque

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

from smart_surveillance_interfaces.msg import (
    DetectedObjects,
    ObjectDepth,
    SceneAnalysis,
    SecurityEvent,
    SecurityAlert,
)


# ── helpers ────────────────────────────────────────────────────────────── #

def _age(ts: float) -> str:
    """Return human-readable age string, or 'NO DATA' if ts is None."""
    if ts is None:
        return 'NO DATA'
    a = time.time() - ts
    if a < 2.0:
        return f'{a:.1f}s  ✓'
    return f'{a:.1f}s  ✗'


def _trunc(s: str, n: int = 40) -> str:
    return s if len(s) <= n else s[:n - 1] + '…'


# ── node ───────────────────────────────────────────────────────────────── #

class SystemMonitorNode(Node):
    def __init__(self):
        super().__init__('system_monitor_node')

        # ── last-seen timestamps (None = never received) ── #
        self._ts = {
            '/camera_frames':    None,
            '/detected_objects': None,
            '/object_depth':     None,
            '/scene_analysis':   None,
            '/security_event':   None,
            '/security_alert':   None,
        }

        # ── latest payload snapshots ── #
        self._detections: list[str]  = []
        self._depths:     list[str]  = []
        self._dangerous:  list[str]  = []
        self._last_event:  str = '—'
        self._last_alert:  str = '—'

        # ── session counters ── #
        self._event_count = 0
        self._alert_count = 0
        self._frame_count = 0

        # ── rolling FPS (last 30 frame timestamps) ── #
        self._frame_times: deque = deque(maxlen=30)

        # ── subscribers ── #
        self.create_subscription(
            Image,            '/camera_frames',    self._cb_frames,    10)
        self.create_subscription(
            DetectedObjects,  '/detected_objects', self._cb_detections, 10)
        self.create_subscription(
            ObjectDepth,      '/object_depth',     self._cb_depth,     10)
        self.create_subscription(
            SceneAnalysis,    '/scene_analysis',   self._cb_scene,     10)
        self.create_subscription(
            SecurityEvent,    '/security_event',   self._cb_event,     10)
        self.create_subscription(
            SecurityAlert,    '/security_alert',   self._cb_alert,     10)

        # ── 1 Hz display timer ── #
        self.create_timer(1.0, self._display)

        self.get_logger().info('System Monitor Node started')

    # ── callbacks ──────────────────────────────────────────────────────── #

    def _cb_frames(self, _msg: Image):
        now = time.time()
        self._ts['/camera_frames'] = now
        self._frame_count += 1
        self._frame_times.append(now)

    def _cb_detections(self, msg: DetectedObjects):
        self._ts['/detected_objects'] = time.time()
        self._detections = [
            f'{lbl}({conf:.0%})'
            for lbl, conf in zip(msg.labels, msg.confidences)
        ]

    def _cb_depth(self, msg: ObjectDepth):
        self._ts['/object_depth'] = time.time()
        self._depths = [
            f'{lbl}:{d:.2f}'
            for lbl, d in zip(msg.labels, msg.depths)
        ]

    def _cb_scene(self, msg: SceneAnalysis):
        self._ts['/scene_analysis'] = time.time()
        self._dangerous = [
            msg.labels[i]
            for i in range(len(msg.labels))
            if msg.is_dangerous[i]
        ]

    def _cb_event(self, msg: SecurityEvent):
        self._ts['/security_event'] = time.time()
        self._event_count += 1
        self._last_event = (
            f'{msg.event_type}  obj={msg.object_label}  '
            f'sev={msg.severity}  depth={msg.object_depth:.2f}'
        )

    def _cb_alert(self, msg: SecurityAlert):
        self._ts['/security_alert'] = time.time()
        self._alert_count += 1
        self._last_alert = msg.alert_message

    # ── display ────────────────────────────────────────────────────────── #

    def _fps(self) -> str:
        if len(self._frame_times) < 2:
            return '—'
        elapsed = self._frame_times[-1] - self._frame_times[0]
        if elapsed <= 0:
            return '—'
        return f'{(len(self._frame_times) - 1) / elapsed:.1f}'

    def _display(self):
        W = 62
        sep  = '─' * W
        dsep = '═' * W

        lines = [
            '',
            dsep,
            '  SMART SURVEILLANCE — SYSTEM MONITOR'.center(W),
            dsep,
            '',
            '  TOPIC HEALTH',
            sep,
        ]

        for topic, ts in self._ts.items():
            lines.append(f'  {topic:<26}  {_age(ts)}')

        lines += [
            '',
            sep,
            f'  Camera FPS (rolling 30):  {self._fps()}',
            f'  Total frames received:    {self._frame_count}',
            sep,
            '',
            '  LATEST DETECTIONS',
            sep,
            f'  Objects : {_trunc(", ".join(self._detections) or "none")}',
            f'  Depths  : {_trunc(", ".join(self._depths)     or "none")}',
            f'  Danger  : {_trunc(", ".join(self._dangerous)  or "none")}',
            '',
            '  SECURITY',
            sep,
            f'  Events  (total): {self._event_count}',
            f'  Alerts  (total): {self._alert_count}',
            f'  Last event : {_trunc(self._last_event)}',
            f'  Last alert : {_trunc(self._last_alert)}',
            dsep,
            '',
        ]

        print('\n'.join(lines), flush=True)


# ── main ───────────────────────────────────────────────────────────────── #

def main(args=None):
    rclpy.init(args=args)
    node = SystemMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
