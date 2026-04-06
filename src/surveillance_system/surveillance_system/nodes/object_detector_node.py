#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO

class ObjectDetectionNode(Node):
    def __init__(self):
        super().__init__('object_detection_node')

        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('model_path', 'yolov8n.pt')

        self.conf_threshold = self.get_parameter('confidence_threshold').value
        self.model_path = self.get_parameter('model_path').value

        self.model = YOLO(self.model_path)

        self.subscription = self.create_subscription(
            Image,
            '/camera_frames',
            self.image_callback,
            10
        )

        self.publisher_ = self.create_publisher(String, '/detected_objects', 10)
        self.bridge = CvBridge()
        self.get_logger().info("Object Detection Node started")

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        results = self.model(frame, device='cpu', verbose=False)

        detections = []

        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < self.conf_threshold:
                    continue

                cls = int(box.cls[0])
                label = self.model.names[cls]

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(f"{label} {conf:.2f} [{x1},{y1},{x2},{y2}]")

        msg_out = String()
        msg_out.data = "; ".join(detections)
        self.publisher_.publish(msg_out)

def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down detection node")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()