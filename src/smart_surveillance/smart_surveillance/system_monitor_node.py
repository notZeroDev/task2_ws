#!/usr/bin/env python3

import time
from collections import deque

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

from smart_surveillance_interfaces.msg import DetectedObjects, ObjectDepth, SceneAnalysis, SecurityEvent, SecurityAlert


class SystemMonitorNode(Node):
    def __init__(self):
        super().__init__('system_monitor_node')

        self._last_seen = {
            '/camera_frames': None,
            '/detected_objects': None,
            '/object_depth': None,
            '/scene_analysis': None,
            '/security_event': None,
            '/security_alert': None,
        }

        self._detections = []
        self._depths = []
        self._dangerous = []
        self._last_event = 'none'
        self._last_alert = 'none'
        self._event_count = 0
        self._alert_count = 0
        self._frame_count = 0
        self._frame_times = deque(maxlen=30)

        self.create_subscription(Image, '/camera_frames', self.frames_callback, 10)
        self.create_subscription(DetectedObjects, '/detected_objects', self.detections_callback, 10)
        self.create_subscription(ObjectDepth, '/object_depth', self.depth_callback, 10)
        self.create_subscription(SceneAnalysis, '/scene_analysis', self.scene_callback, 10)
        self.create_subscription(SecurityEvent, '/security_event', self.event_callback, 10)
        self.create_subscription(SecurityAlert, '/security_alert', self.alert_callback, 10)

        self.create_timer(1.0, self.display)
        self.get_logger().info('System Monitor Node started')

    def frames_callback(self, _msg):
        now = time.time()
        self._last_seen['/camera_frames'] = now
        self._frame_count += 1
        self._frame_times.append(now)

    def detections_callback(self, msg):
        self._last_seen['/detected_objects'] = time.time()
        self._detections = [f'{l}({c:.0%})' for l, c in zip(msg.labels, msg.confidences)]

    def depth_callback(self, msg):
        self._last_seen['/object_depth'] = time.time()
        self._depths = [f'{l}:{d:.2f}' for l, d in zip(msg.labels, msg.depths)]

    def scene_callback(self, msg):
        self._last_seen['/scene_analysis'] = time.time()
        self._dangerous = [msg.labels[i] for i in range(len(msg.labels)) if msg.is_dangerous[i]]

    def event_callback(self, msg):
        self._last_seen['/security_event'] = time.time()
        self._event_count += 1
        self._last_event = f'{msg.event_type} | {msg.object_label} | sev={msg.severity}'

    def alert_callback(self, msg):
        self._last_seen['/security_alert'] = time.time()
        self._alert_count += 1
        self._last_alert = msg.alert_message

    def fps(self):
        if len(self._frame_times) < 2:
            return 0.0
        elapsed = self._frame_times[-1] - self._frame_times[0]
        return (len(self._frame_times) - 1) / elapsed if elapsed > 0 else 0.0

    def display(self):
        print('\n--- SYSTEM MONITOR ---')
        for topic, ts in self._last_seen.items():
            if ts is None:
                status = 'NO DATA'
            elif time.time() - ts < 2.0:
                status = 'OK'
            else:
                status = 'STALE'
            print(f'  {topic}: {status}')

        print(f'  FPS: {self.fps():.1f}  |  Frames: {self._frame_count}')
        print(f'  Detections: {self._detections or "none"}')
        print(f'  Dangerous:  {self._dangerous or "none"}')
        print(f'  Events: {self._event_count}  |  Last: {self._last_event}')
        print(f'  Alerts: {self._alert_count}  |  Last: {self._last_alert}')


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