#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from smart_surveillance_interfaces.msg import DetectedObjects


class ObjectDetectionNode(Node):
    def __init__(self):
        super().__init__('object_detection_node')

        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('model_path', 'yolov8n.pt')

        self.conf_threshold = self.get_parameter('confidence_threshold').value
        self.model_path = self.get_parameter('model_path').value

        from ultralytics import YOLO
        self.model = YOLO(self.model_path)

        self.subscription = self.create_subscription(
            Image, '/camera_frames', self.image_callback, 10)

        self.publisher_ = self.create_publisher(
            DetectedObjects, '/detected_objects', 10)

        self.bridge = CvBridge()
        self.get_logger().info('Object Detection Node started')

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        results = self.model(frame)

        out = DetectedObjects()
        out.header = msg.header

        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < self.conf_threshold:
                    continue
                cls = int(box.cls[0])
                label = self.model.names[cls]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                out.labels.append(label)
                out.confidences.append(conf)
                out.x1.append(x1)
                out.y1.append(y1)
                out.x2.append(x2)
                out.y2.append(y2)

        self.publisher_.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
