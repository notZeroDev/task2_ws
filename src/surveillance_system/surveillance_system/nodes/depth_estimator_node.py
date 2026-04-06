#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class DepthEstimatorNode(Node):
    def __init__(self):
        super().__init__('depth_estimator_node')
        self.get_logger().info("Depth Estimator Node (Placeholder)")

def main(args=None):
    rclpy.init(args=args)
    node = DepthEstimatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
