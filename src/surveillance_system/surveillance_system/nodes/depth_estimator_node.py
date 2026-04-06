#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge

import sys
import os
import cv2
import numpy as np
import torch
import concurrent.futures

# Add Depth-Anything-V2 to sys.path
sys.path.append('/root/task2_ws/Depth-Anything-V2')
from depth_anything_v2.dpt import DepthAnythingV2

class DepthEstimatorNode(Node):
    def __init__(self):
        super().__init__('depth_estimator_node')

        # Parameters
        self.declare_parameter('depth_model_path', '/root/task2_ws/checkpoints/depth_anything_v2_vits.pth')
        self.declare_parameter('encoder', 'vits')
        self.declare_parameter('process_every_n', 3)
        self.declare_parameter('near_threshold', 0.65)
        self.declare_parameter('input_size', 392)

        self.model_path = self.get_parameter('depth_model_path').value
        self.encoder = self.get_parameter('encoder').value
        self.process_every_n = self.get_parameter('process_every_n').value
        self.near_threshold = self.get_parameter('near_threshold').value
        self.input_size = self.get_parameter('input_size').value

        self.frame_count = 0

        # Load the model
        self.get_logger().info(f"Loading DepthAnythingV2 ({self.encoder})...")
        model_configs = {
            'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
            'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
            'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
            'vitg': {'encoder': 'vitg', 'features': 384, 'out_channels': [1536, 1536, 1536, 1536]}
        }
        
        self.device = 'cpu'
        self.model = DepthAnythingV2(**model_configs[self.encoder])
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model = self.model.to(self.device).eval()
        self.get_logger().info(f"DepthAnythingV2 loaded — CPU mode")

        # Sub/Pub
        self.subscription = self.create_subscription(
            Image,
            '/camera_frames',
            self.image_callback,
            2
        )
        self.publisher_ = self.create_publisher(String, '/object_depth', 10)
        
        self.bridge = CvBridge()
        
        # ThreadPoolExecutor for non-blocking inference
        self.thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.future = None

    def image_callback(self, msg):
        self.frame_count += 1
        
        if self.frame_count % self.process_every_n != 0:
            return

        # Ensure we don't queue multiple inferences if CPU is lagging
        if self.future is not None and not self.future.done():
            return
            
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        # Submit to executor
        self.future = self.thread_executor.submit(self.infer_depth, frame)
        self.future.add_done_callback(self.publish_result)

    def infer_depth(self, frame):
        # Resize inside the worker thread
        h, w = frame.shape[:2]
        # model.infer_image expects BGR input and input_size
        depth = self.model.infer_image(frame, input_size=self.input_size)
        
        # Depth is raw disparity, normalize to 0-1 for scene analyzer
        depth_min, depth_max = depth.min(), depth.max()
        if depth_max > depth_min:
            depth_norm = (depth - depth_min) / (depth_max - depth_min)
        else:
            depth_norm = depth
            
        # Compute overall stats
        avg_depth = float(np.mean(depth_norm))
        near_ratio = float(np.mean(depth_norm > self.near_threshold))
        
        # Optional: return bounds for advanced debugging
        return f"avg_depth={avg_depth:.2f}; near_ratio={near_ratio:.2f}; min={depth_min:.2f}; max={depth_max:.2f}"

    def publish_result(self, future):
        try:
            result_str = future.result()
            msg = String()
            msg.data = result_str
            self.publisher_.publish(msg)
        except Exception as e:
            self.get_logger().error(f"Inference failed: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = DepthEstimatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down depth estimator node")
    finally:
        node.thread_executor.shutdown(wait=False)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
