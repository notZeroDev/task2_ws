#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Header

from perception_interfaces.msg import SceneAnalysis, SecurityEvent


class EventManagerNode(Node):
    def __init__(self):
        super().__init__("event_manager_node")

        # --- Parameters ---
        self.declare_parameter("restricted_objects", ["person"])
        self.declare_parameter("alert_threshold_depth", 0.5)

        self.restricted_objects = [
            o.lower() for o in self.get_parameter("restricted_objects").value
        ]
        self.alert_threshold_depth = self.get_parameter("alert_threshold_depth").value

        # --- Subscriber ---
        self.create_subscription(
            SceneAnalysis, "/scene_analysis", self.scene_callback, 10
        )

        # --- Publisher ---
        self.publisher_ = self.create_publisher(SecurityEvent, "/security_event", 10)

        self.get_logger().info("Event Manager Node started")
        self.get_logger().info(f"  restricted_objects = {self.restricted_objects}")
        self.get_logger().info(
            f"  alert_threshold_depth = {self.alert_threshold_depth}"
        )

    def scene_callback(self, msg: SceneAnalysis):
        """
        Process scene analysis and identify security events.
        Events include:
        - TOO_CLOSE: Object closer than threshold
        - UNUSUAL_OBJECT: Knife, scissors, gun, etc.
        - RESTRICTED_AREA: Person detected in restricted area
        """
        frame_id = msg.header.frame_id

        for obj in msg.objects:
            label = obj.class_name.lower()
            depth = obj.mean_depth
            flags = obj.flags

            # Determine event type and severity
            event_type = None
            severity = "LOW"

            # Check for TOO_CLOSE
            if "TOO_CLOSE" in flags:
                event_type = "TOO_CLOSE"
                severity = "HIGH"
                self._publish_event(
                    msg.header, event_type, obj.class_name, depth, severity
                )

            # Check for UNUSUAL_OBJECT
            if "UNUSUAL_OBJECT" in flags:
                event_type = "UNUSUAL_OBJECT"
                severity = "CRITICAL"
                self._publish_event(
                    msg.header, event_type, obj.class_name, depth, severity
                )

            # Check for RESTRICTED_AREA (person detected)
            if label in self.restricted_objects:
                event_type = "RESTRICTED_AREA"
                severity = "MEDIUM"
                self._publish_event(
                    msg.header, event_type, obj.class_name, depth, severity
                )

    def _publish_event(
        self,
        header: Header,
        event_type: str,
        object_label: str,
        depth: float,
        severity: str,
    ):
        """Publish a security event."""
        event_msg = SecurityEvent()
        event_msg.header = header
        event_msg.event_type = event_type
        event_msg.object_label = object_label
        event_msg.object_depth = depth
        event_msg.severity = severity

        self.publisher_.publish(event_msg)
        self.get_logger().warn(
            f"[EVENT] {event_type} | obj={object_label} | "
            f"depth={depth:.3f} | severity={severity}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = EventManagerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down event manager node")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
