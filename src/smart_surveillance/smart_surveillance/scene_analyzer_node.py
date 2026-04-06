#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from message_filters import ApproximateTimeSynchronizer, Subscriber

from smart_surveillance_interfaces.msg import (
    DetectedObjects,
    ObjectDepth,
    SceneAnalysis,
)


class SceneAnalyzerNode(Node):
    def __init__(self):
        super().__init__('scene_analyzer_node')

        # Parameter: depth value above which an object is flagged dangerous
        # (0.0-1.0 normalised scale — higher means closer to camera)
        self.declare_parameter('danger_distance', 0.75)
        self.danger_distance = self.get_parameter('danger_distance').value

        # Publisher
        self.publisher_ = self.create_publisher(SceneAnalysis, '/scene_analysis', 10)

        # Synchronised subscribers — wait up to 0.1 s for a matching pair
        self.det_sub = Subscriber(self, DetectedObjects, '/detected_objects')
        self.dep_sub = Subscriber(self, ObjectDepth,     '/object_depth')

        self.sync = ApproximateTimeSynchronizer(
            [self.det_sub, self.dep_sub],
            queue_size=10,
            slop=0.1,
        )
        self.sync.registerCallback(self.sync_callback)

        self.get_logger().info(
            f'Scene Analyzer Node started  (danger_distance={self.danger_distance})')

    def sync_callback(self, det_msg: DetectedObjects, dep_msg: ObjectDepth):
        """Combine detection + depth; flag objects that are too close."""

        out = SceneAnalysis()
        out.header = det_msg.header

        # det_msg and dep_msg should have the same labels/boxes because
        # depth_estimator forwards them unchanged.  Use det_msg as source
        # of truth for geometry; dep_msg for depth values.
        n = len(det_msg.labels)
        dep_n = len(dep_msg.depths)

        for i in range(n):
            depth_val = dep_msg.depths[i] if i < dep_n else 0.0
            is_dangerous = depth_val >= self.danger_distance

            out.labels.append(det_msg.labels[i])
            out.depths.append(depth_val)
            out.is_dangerous.append(is_dangerous)
            out.x1.append(det_msg.x1[i])
            out.y1.append(det_msg.y1[i])
            out.x2.append(det_msg.x2[i])
            out.y2.append(det_msg.y2[i])

            if is_dangerous:
                self.get_logger().debug(
                    f'Dangerous object: {det_msg.labels[i]}  '
                    f'depth={depth_val:.2f}')

        self.publisher_.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = SceneAnalyzerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
