#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class SecurityResponseNode(Node):
    def __init__(self):
        super().__init__('security_response_node')
        self.get_logger().info("Security Response Node (Placeholder)")

def main(args=None):
    rclpy.init(args=args)
    node = SecurityResponseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
