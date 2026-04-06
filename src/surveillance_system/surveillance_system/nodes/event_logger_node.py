#!/usr/bin/env python3

import os
import csv
from datetime import datetime

import rclpy
from rclpy.node import Node

from perception_interfaces.msg import SecurityEvent, SecurityAlert


class EventLoggerNode(Node):
    def __init__(self):
        super().__init__("event_logger_node")

        self.declare_parameter("log_file", "surveillance_log.csv")
        log_file = self.get_parameter("log_file").value

        self._open_log(log_file)

        # Subscribers
        self.create_subscription(
            SecurityEvent,
            "/security_event",
            self.event_callback,
            10,
        )
        self.create_subscription(
            SecurityAlert,
            "/security_alert",
            self.alert_callback,
            10,
        )

        self.get_logger().info(f"Event Logger Node started  (log={log_file})")

    def _open_log(self, path: str):
        file_exists = os.path.isfile(path)
        self._log_fh = open(path, "a", newline="")
        self._csv = csv.writer(self._log_fh)
        if not file_exists:
            self._csv.writerow(
                [
                    "timestamp",
                    "record_type",
                    "event_type",
                    "object_label",
                    "depth",
                    "severity",
                    "message",
                ]
            )
            self._log_fh.flush()

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def event_callback(self, msg: SecurityEvent):
        row = [
            self._now(),
            "EVENT",
            msg.event_type,
            msg.object_label,
            f"{msg.object_depth:.3f}",
            msg.severity,
            "",
        ]
        self._csv.writerow(row)
        self._log_fh.flush()
        self.get_logger().info(
            f"[LOG EVENT] {msg.event_type}  "
            f"obj={msg.object_label}  "
            f"depth={msg.object_depth:.2f}  "
            f"sev={msg.severity}"
        )

    def alert_callback(self, msg: SecurityAlert):
        row = [
            self._now(),
            "ALERT",
            msg.triggered_by,
            "",
            "",
            msg.alert_level,
            msg.alert_message,
        ]
        self._csv.writerow(row)
        self._log_fh.flush()
        self.get_logger().warn(f"[LOG ALERT] {msg.alert_message}")

    def destroy_node(self):
        if hasattr(self, "_log_fh") and self._log_fh:
            self._log_fh.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = EventLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
