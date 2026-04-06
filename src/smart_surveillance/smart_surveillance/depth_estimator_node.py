#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np
import cv2
import torch

from smart_surveillance_interfaces.msg import DetectedObjects, ObjectDepth


class DepthEstimatorNode(Node):
    def __init__(self):
        super().__init__('depth_estimator_node')

        # Parameters
        self.declare_parameter('depth_model_path', 'depth_anything_v2_vits.pth')
        self.declare_parameter('model_size', 'vits')   # vits | vitb | vitl
        self.depth_model_path = self.get_parameter('depth_model_path').value
        self.model_size = self.get_parameter('model_size').value

        self.bridge = CvBridge()
        self.latest_frame = None
        self.model = None

        # Load model
        self._load_model()

        # Subscribers
        self.create_subscription(
            Image,
            '/camera_frames',
            self.frame_callback,
            10)

        self.create_subscription(
            DetectedObjects,
            '/detected_objects',
            self.detection_callback,
            10)

        # Publisher
        self.publisher_ = self.create_publisher(ObjectDepth, '/object_depth', 10)

        self.get_logger().info('Depth Estimator Node started')

    # ------------------------------------------------------------------ #
    #  Model loading                                                       #
    # ------------------------------------------------------------------ #
    def _load_model(self):
        """Load DepthAnythingV2. Falls back to a dummy if weights missing."""
        try:
            from depth_anything_v2.dpt import DepthAnythingV2 as DAV2

            configs = {
                'vits': {'encoder': 'vits', 'features': 64,
                         'out_channels': [48, 96, 192, 384]},
                'vitb': {'encoder': 'vitb', 'features': 128,
                         'out_channels': [96, 192, 384, 768]},
                'vitl': {'encoder': 'vitl', 'features': 256,
                         'out_channels': [256, 512, 1024, 1024]},
            }
            cfg = configs.get(self.model_size, configs['vits'])
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

            self.model = DAV2(**cfg)
            self.model.load_state_dict(
                torch.load(self.depth_model_path,
                           map_location=self.device))
            self.model = self.model.to(self.device).eval()
            self.get_logger().info(
                f'DepthAnythingV2 loaded ({self.model_size}) on {self.device}')

        except Exception as e:
            self.get_logger().warn(
                f'Could not load DepthAnythingV2: {e}\n'
                'Running in FALLBACK mode (normalised inverse intensity).')
            self.model = None

    # ------------------------------------------------------------------ #
    #  Callbacks                                                           #
    # ------------------------------------------------------------------ #
    def frame_callback(self, msg: Image):
        """Cache the latest frame — depth is computed on detection arrival."""
        self.latest_frame = msg

    def detection_callback(self, det_msg: DetectedObjects):
        """For every detection, sample depth at bounding-box centre."""
        if self.latest_frame is None:
            return

        if not det_msg.labels:          # nothing detected — still publish empty
            out = ObjectDepth()
            out.header = det_msg.header
            self.publisher_.publish(out)
            return

        # Convert ROS Image → OpenCV BGR → RGB float
        frame_bgr = self.bridge.imgmsg_to_cv2(
            self.latest_frame, desired_encoding='bgr8')
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        depth_map = self._infer_depth(frame_rgb)   # H×W float32, normalised 0-1

        out = ObjectDepth()
        out.header = det_msg.header
        out.labels = det_msg.labels
        out.x1 = det_msg.x1
        out.y1 = det_msg.y1
        out.x2 = det_msg.x2
        out.y2 = det_msg.y2

        h, w = depth_map.shape
        for i in range(len(det_msg.labels)):
            cx = (det_msg.x1[i] + det_msg.x2[i]) // 2
            cy = (det_msg.y1[i] + det_msg.y2[i]) // 2
            cx = max(0, min(cx, w - 1))
            cy = max(0, min(cy, h - 1))
            out.depths.append(float(depth_map[cy, cx]))

        self.publisher_.publish(out)

    # ------------------------------------------------------------------ #
    #  Depth inference                                                     #
    # ------------------------------------------------------------------ #
    def _infer_depth(self, frame_rgb: np.ndarray) -> np.ndarray:
        """Return a normalised depth map (0 = far, 1 = close)."""
        if self.model is not None:
            return self._infer_dav2(frame_rgb)
        return self._infer_fallback(frame_rgb)

    def _infer_dav2(self, frame_rgb: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            depth = self.model.infer_image(frame_rgb)  # H×W numpy
        # Normalise to 0-1  (higher = closer)
        d_min, d_max = depth.min(), depth.max()
        if d_max - d_min > 1e-6:
            depth = (depth - d_min) / (d_max - d_min)
        return depth.astype(np.float32)

    def _infer_fallback(self, frame_rgb: np.ndarray) -> np.ndarray:
        """Cheap proxy: bright pixels tend to be closer in indoor scenes."""
        gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        gray /= 255.0
        return gray


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
