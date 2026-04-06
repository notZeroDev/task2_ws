#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import Header
from datetime import datetime

from perception_interfaces.msg import SecurityEvent, SecurityAlert


class SecurityResponseNode(Node):
    def __init__(self):
        super().__init__("security_response_node")

        # --- Parameters ---
        self.declare_parameter("alert_level", "MEDIUM")
        self.declare_parameter("enable_notifications", True)
        self.declare_parameter("enable_recording", True)
        self.declare_parameter("enable_alarms", True)

        self.default_alert_level = self.get_parameter("alert_level").value
        self.enable_notifications = self.get_parameter("enable_notifications").value
        self.enable_recording = self.get_parameter("enable_recording").value
        self.enable_alarms = self.get_parameter("enable_alarms").value

        # --- Subscriber ---
        self.create_subscription(
            SecurityEvent, "/security_event", self.event_callback, 10
        )

        # --- Publisher ---
        self.publisher_ = self.create_publisher(SecurityAlert, "/security_alert", 10)

        # Track active alerts to avoid duplicate notifications
        self.active_alerts = {}

        self.get_logger().info("Security Response Node started")
        self.get_logger().info(f"  default_alert_level = {self.default_alert_level}")
        self.get_logger().info(f"  enable_notifications = {self.enable_notifications}")
        self.get_logger().info(f"  enable_recording = {self.enable_recording}")
        self.get_logger().info(f"  enable_alarms = {self.enable_alarms}")

    def event_callback(self, msg: SecurityEvent):
        """
        Process security events and trigger appropriate responses.
        Maps event severity to alert level and triggers corresponding actions.
        """
        event_type = msg.event_type
        severity = msg.severity
        object_label = msg.object_label

        # Determine alert level based on event severity
        alert_level = self._map_severity_to_level(severity)

        # Generate alert message
        alert_message = self._generate_alert_message(
            event_type, object_label, msg.object_depth
        )

        # Check for duplicate alerts (same event type within short time window)
        alert_key = f"{event_type}_{object_label}"
        if not self._should_raise_alert(alert_key):
            self.get_logger().debug(f"Suppressing duplicate alert: {alert_key}")
            return

        # Trigger responses based on alert level
        self._trigger_responses(severity)

        # Publish security alert
        self._publish_alert(msg.header, event_type, alert_level, alert_message)

    def _map_severity_to_level(self, severity: str) -> str:
        """Map event severity to alert level."""
        severity_map = {
            "CRITICAL": "CRITICAL",
            "HIGH": "HIGH",
            "MEDIUM": "MEDIUM",
            "LOW": "LOW",
        }
        return severity_map.get(severity, self.default_alert_level)

    def _generate_alert_message(
        self, event_type: str, object_label: str, depth: float
    ) -> str:
        """Generate a descriptive alert message."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if event_type == "TOO_CLOSE":
            return f"[{timestamp}] ALERT: {object_label} detected too close (depth: {depth:.2f})"
        elif event_type == "UNUSUAL_OBJECT":
            return (
                f"[{timestamp}] CRITICAL: Suspicious object detected - {object_label}"
            )
        elif event_type == "RESTRICTED_AREA":
            return f"[{timestamp}] ALERT: {object_label} detected in restricted area"
        else:
            return f"[{timestamp}] ALERT: {event_type} - {object_label}"

    def _should_raise_alert(self, alert_key: str) -> bool:
        """
        Check if this alert should be raised (de-duplication).
        Currently allows all alerts; can be extended with time-based filtering.
        """
        # Always raise new alerts (can be enhanced with cooldown timers)
        return True

    def _trigger_responses(self, severity: str):
        """
        Trigger security response actions based on alert severity.
        Could integrate with:
        - Video recording systems
        - Alarm systems
        - Notification systems
        - Access control systems
        """
        if severity == "CRITICAL":
            if self.enable_alarms:
                self._trigger_alarm()
            if self.enable_notifications:
                self._send_notification("CRITICAL", "CRITICAL security event!")
            if self.enable_recording:
                self._start_recording()
        elif severity == "HIGH":
            if self.enable_notifications:
                self._send_notification("HIGH", "High-priority security event!")
            if self.enable_recording:
                self._start_recording()
        elif severity == "MEDIUM":
            if self.enable_notifications:
                self._send_notification("MEDIUM", "Medium-priority security event")

    def _trigger_alarm(self):
        """Trigger physical alarm system."""
        self.get_logger().error("[ALARM] CRITICAL SECURITY ALERT! Alarm triggered!")
        # Integration point: Send signal to alarm system

    def _send_notification(self, level: str, message: str):
        """Send notification to security personnel."""
        self.get_logger().warn(f"[NOTIFICATION] [{level}] {message}")
        # Integration point: Send email, SMS, push notification, etc.

    def _start_recording(self):
        """Start or enhance video recording."""
        self.get_logger().info("[RECORDING] Initiating enhanced video recording")
        # Integration point: Signal to camera/recorder to start high-resolution recording

    def _publish_alert(
        self, header: Header, triggered_by: str, alert_level: str, alert_message: str
    ):
        """Publish a security alert message."""
        alert_msg = SecurityAlert()
        alert_msg.header = header
        alert_msg.triggered_by = triggered_by
        alert_msg.alert_level = alert_level
        alert_msg.alert_message = alert_message

        self.publisher_.publish(alert_msg)
        self.get_logger().warn(f"[ALERT] {alert_message}")


def main(args=None):
    rclpy.init(args=args)
    node = SecurityResponseNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down security response node")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
