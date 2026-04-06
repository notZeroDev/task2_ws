#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from smart_surveillance_interfaces.msg import SceneAnalysis, SecurityEvent


class EventManagerNode(Node):
    def __init__(self):
        super().__init__('event_manager_node')

        self.declare_parameter('restricted_objects', 'knife,scissors,cell phone')
        restricted_raw = self.get_parameter('restricted_objects').value
        self.restricted_objects = [
            s.strip().lower() for s in restricted_raw.split(',') if s.strip()
        ]

        # Subscriber
        self.create_subscription(
            SceneAnalysis,
            '/scene_analysis',
            self.scene_callback,
            10,
        )

        # Publisher
        self.publisher_ = self.create_publisher(SecurityEvent, '/security_event', 10)

        self.get_logger().info(
            f'Event Manager Node started  '
            f'(restricted={self.restricted_objects})'
        )

    # ------------------------------------------------------------------ #

    def scene_callback(self, msg: SceneAnalysis):
        n = len(msg.labels)
        for i in range(n):
            label = msg.labels[i].lower()
            depth = msg.depths[i]
            dangerous = msg.is_dangerous[i]

            event_type = None
            severity = 1

            # Rule 1 — restricted object in frame
            if label in self.restricted_objects:
                event_type = 'restricted_object_detected'
                severity = 3

            # Rule 2 — any object too close to camera
            elif dangerous:
                event_type = 'object_too_close'
                severity = 2

            # Rule 3 — person detected (always worth logging at low severity)
            elif label == 'person':
                event_type = 'person_in_frame'
                severity = 1

            if event_type is None:
                continue

            evt = SecurityEvent()
            evt.header = msg.header
            evt.event_type = event_type
            evt.object_label = msg.labels[i]
            evt.object_depth = depth
            evt.severity = severity

            self.publisher_.publish(evt)
            self.get_logger().info(
                f'[EVENT] {event_type}  '
                f'object={msg.labels[i]}  '
                f'depth={depth:.2f}  '
                f'severity={severity}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = EventManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
