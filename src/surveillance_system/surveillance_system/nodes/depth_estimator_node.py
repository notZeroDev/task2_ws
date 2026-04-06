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

# sys.path.append('/ros2/task2_ws/Depth-Anything-V2')
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up 3 levels: nodes -> surveillance_system -> surveillance_system -> src -> TASK2_WS
ws_root = os.path.join(script_dir, "../../../..") 
sys.path.append(os.path.join(ws_root, 'Depth-Anything-V2'))

from depth_anything_v2.dpt import DepthAnythingV2

class DepthEstimatorNode(Node):
    def __init__(self):
        super().__init__('depth_estimator_node')

        # Parameters
        self.declare_parameter('depth_model_path', '/home/youssef/ros2/task2_ws/checkpoints/depth_anything_v2_vits.pth')
        self.declare_parameter('encoder', 'vits')
        self.declare_parameter('process_every_n', 3)
        self.declare_parameter('near_threshold', 0.65)
        self.declare_parameter('input_size', 392)

        self.model_path = self.get_parameter('depth_model_path').value
        self.encoder = self.get_parameter('encoder').value
        self.process_every_n = self.get_parameter('process_every_n').value
        self.near_threshold = self.get_parameter('near_threshold').value
        self.input_size = self.get_parameter('input_size').value

        # self.frame_count = 0
        # self.depth_frame_id = 0

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
        self.publisher_ = self.create_publisher(Image, '/object_depth', 10)
        
        self.bridge = CvBridge()
        
        # ThreadPoolExecutor for non-blocking inference
        self.thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.future = None

    def image_callback(self, msg):
        # extract info from image
        self.img_msg_header = msg.header
        msg_timestamp =  self.img_msg_header.stamp
        msg_frame_id =  self.img_msg_header.frame_id
        
        # if self.frame_count % self.process_every_n != 0:
        #     return

        # Ensure we don't queue multiple inferences if CPU is lagging
        if self.future is not None and not self.future.done():
            return
            
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        
        # Submit to executor, passing current frame_id
        self.future = self.thread_executor.submit(self.infer_depth, frame, msg_frame_id)
        self.future.add_done_callback(self.publish_result)
        

    def infer_depth(self, frame, frame_id):
        # 1. Inference
        depth_map = self.model.infer_image(frame, input_size=self.input_size)
        
        # 2. Create the ROS message
        depth_msg = self.bridge.cv2_to_imgmsg(depth_map.astype(np.float32), encoding='32FC1')
        depth_msg.header = self.img_msg_header
        
        # Fix: Use depth_map here, not depth
        self.get_logger().info(f"Depth estimation frame {frame_id} | depth_map shape {depth_map.shape}")
        
        # 3. Visualization Logic
        depth_min, depth_max = depth_map.min(), depth_map.max()
        if depth_max > depth_min:
            depth_vis = 255*(depth_map - depth_min) / (depth_max - depth_min)
        else:
            depth_vis = np.zeros_like(depth_vis, 0, 255)

        depth_vis = np.clip(depth_vis, 0, 255).astype(np.uint8)
        # depth_colored = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)    

        # depth_resized = cv2.resize(depth_colored, (0, 0), fx=0.5, fy=0.5)
        # frame_resized = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        # combined_view = np.hstack((frame_resized, depth_resized))

        # cv2.imshow("Depth_Estimation", combined_view)
        # cv2.waitKey(1)
        
        return depth_msg

    def publish_result(self, future):
        try:
            msg = future.result()
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
