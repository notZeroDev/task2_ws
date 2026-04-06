import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from rcl_interfaces.msg import SetParametersResult

class CameraStreamNode(Node):
    def __init__(self):
        super().__init__('camera_stream_node')
        
        # Declare parameters
        self.declare_parameter('camera_source', '0')
        self.declare_parameter('frame_rate', 30.0)

        self.bridge = CvBridge()
        self.publisher_ = self.create_publisher(Image, '/camera_frames', 10)
        
        self.cap = None
        self.stream_timer = None
        self.reconfig_timer = None
        
        # Initial setup
        self.setup_capture()

        # Parameter change callback
        self.add_on_set_parameters_callback(self.parameter_callback)

    def setup_capture(self):
        """Initializes the OpenCV capture and starts the streaming timer."""
        # Cancel the reconfig timer if this was triggered by a parameter change
        if self.reconfig_timer is not None:
            self.reconfig_timer.cancel()
            self.reconfig_timer = None

        source = self.get_parameter('camera_source').value
        fps = self.get_parameter('frame_rate').value
        
        # Safety check for source types
        if str(source).isdigit():
            source = int(source)
            
        # Clean up existing resources
        if self.stream_timer is not None:
            self.stream_timer.cancel()
            self.destroy_timer(self.stream_timer)
            self.stream_timer = None
            
        if self.cap is not None:
            self.cap.release()
            
        # Open camera
        self.cap = cv2.VideoCapture(source)
        
        if not self.cap.isOpened():
            self.get_logger().error(f"Could not open source: {source}")
            return

        # Start the streaming timer
        timer_period = 1.0 / fps
        self.stream_timer = self.create_timer(timer_period, self.timer_callback)
        self.get_logger().info(f"RUNNING: Source={source} at {fps} FPS")

    def parameter_callback(self, params):
        """Triggered when parameters change via CLI/GUI."""
        for param in params:
            if param.name in ['camera_source', 'frame_rate']:
                self.get_logger().info(f"Parameter '{param.name}' updated to {param.value}. Restarting...")
                
                # We use a one-shot timer to trigger setup_capture AFTER this callback returns.
                # This ensures ROS has finished updating the internal parameter values.
                if self.reconfig_timer is not None:
                    self.reconfig_timer.cancel()
                self.reconfig_timer = self.create_timer(0.2, self.setup_capture)
                
        return SetParametersResult(successful=True)

    def timer_callback(self):
        """Main loop that grabs frames and publishes them."""
        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        
        if ret:
            # Convert OpenCV (BGR) to ROS Image message
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "camera_link"
            self.publisher_.publish(msg)
        else:
            # If it's a file, loop back to the start
            source = self.get_parameter('camera_source').value
            if not str(source).isdigit():
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

def main(args=None):
    rclpy.init(args=args)
    node = CameraStreamNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Clean shutdown
        if node.cap:
            node.cap.release()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()