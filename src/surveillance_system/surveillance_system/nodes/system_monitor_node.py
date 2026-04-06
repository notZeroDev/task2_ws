#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class SystemMonitorNode(Node):
    def __init__(self):
        super().__init__('system_monitor_node')
        self.get_logger().info("System Monitor Node (Placeholder)")

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
