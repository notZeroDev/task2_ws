#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np

from perception_interfaces.msg import BoundingBox, DetectionList, SceneAnalysis, SceneObject


class SceneAnalysisNode(Node):
    def __init__(self):
        super().__init__('scene_analysis_node')

        # --- Parameters ---
        self.declare_parameter('danger_distance', 0.65)
        self.declare_parameter('unusual_objects', ['knife', 'scissors', 'bottle', 'gun'])
        self.declare_parameter('buffer_max_size', 60)   # max frames held in buffer before pruning

        self.danger_threshold = self.get_parameter('danger_distance').value
        self.unusual_objects  = [o.lower() for o in self.get_parameter('unusual_objects').value]
        self.buffer_max_size  = self.get_parameter('buffer_max_size').value

        self.bridge = CvBridge()

        # -------------------------------------------------------------------
        # Sync buffer
        # Key   : frame_id (str) — set by CameraStreamNode as str(self.frame_id)
        # Value : {
        #     'frame'      : np.ndarray  | None,
        #     'detections' : DetectionList | None,
        #     'depth'      : np.ndarray (float32, normalized) | None
        # }
        # A frame is processed when all three slots are not None.
        # -------------------------------------------------------------------
        self.buffer: dict[str, dict] = {}

        # --- Subscribers ---
        self.create_subscription(Image,         '/camera_frames',    self.camera_callback,    10)
        self.create_subscription(DetectionList, '/detected_objects', self.detection_callback, 10)
        self.create_subscription(Image,         '/object_depth',     self.depth_callback,     10)

        # --- Publisher ---
        self.publisher_ = self.create_publisher(SceneAnalysis, '/scene_analysis', 10)

        self.get_logger().info("Scene Analysis Node started")
        self.get_logger().info(f"  danger_distance = {self.danger_threshold}")
        self.get_logger().info(f"  unusual_objects = {self.unusual_objects}")

    # -----------------------------------------------------------------------
    # Buffer helpers
    # -----------------------------------------------------------------------

    def _get_or_create_slot(self, frame_id: str) -> dict:
        """Return existing buffer slot or create an empty one."""
        if frame_id not in self.buffer:
            self.buffer[frame_id] = {
                'frame':      None,
                'detections': None,
                'depth':      None,
            }
        return self.buffer[frame_id]

    def _is_complete(self, slot: dict) -> bool:
        return all(v is not None for v in slot.values())

    def _prune_buffer(self, current_frame_id: str):
        """
        Drop old entries to prevent the buffer from growing indefinitely.
        Keeps only frame_ids numerically close to the current one.
        If frame_ids are not numeric, falls back to FIFO by insertion order.
        """
        if len(self.buffer) <= self.buffer_max_size:
            return

        try:
            current = int(current_frame_id)
            # Drop any frame that is more than buffer_max_size behind current
            stale = [fid for fid in self.buffer
                     if current - int(fid) > self.buffer_max_size]
        except ValueError:
            # Non-numeric frame_ids: drop oldest by insertion order
            overflow = len(self.buffer) - self.buffer_max_size
            stale = list(self.buffer.keys())[:overflow]

        for fid in stale:
            del self.buffer[fid]
            self.get_logger().debug(f"Pruned stale frame_id={fid} from buffer")

    # -----------------------------------------------------------------------
    # Callbacks — each one deposits into the buffer, then tries to process
    # -----------------------------------------------------------------------

    def camera_callback(self, msg: Image):
        frame_id = msg.header.frame_id
        slot = self._get_or_create_slot(frame_id)

        # Only decode if not already filled (duplicate guard)
        if slot['frame'] is None:
            slot['frame'] = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        self._try_process(frame_id, msg.header)
        self._prune_buffer(frame_id)

    def detection_callback(self, msg: DetectionList):
        frame_id = msg.header.frame_id
        slot = self._get_or_create_slot(frame_id)

        if slot['detections'] is None:
            slot['detections'] = msg   # keep the whole DetectionList (has header too)

        self._try_process(frame_id, msg.header)
        self._prune_buffer(frame_id)

    def depth_callback(self, msg: Image):
        frame_id = msg.header.frame_id
        slot = self._get_or_create_slot(frame_id)

        if slot['depth'] is None:
            raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding='32FC1')
            slot['depth'] = self._normalize_depth(raw)

        self._try_process(frame_id, msg.header)
        self._prune_buffer(frame_id)

    # -----------------------------------------------------------------------
    # Core processing — runs only when all 3 streams have arrived
    # -----------------------------------------------------------------------

    def _try_process(self, frame_id: str, header):
        slot = self.buffer.get(frame_id)
        if slot is None or not self._is_complete(slot):
            return  # still waiting for one or more streams

        # Pop immediately so we never process the same frame twice
        completed = self.buffer.pop(frame_id)
        frame      = completed['frame']           # np.ndarray  (H, W, 3)
        det_list   = completed['detections']      # DetectionList
        depth_norm = completed['depth']           # np.ndarray  (H', W') float32 [0,1]

        flagged_objects = []

        for bbox in det_list.detections:
            label     = bbox.class_name.lower()
            conf      = bbox.conf
            x1, y1    = bbox.x1, bbox.y1
            x2, y2    = bbox.x2, bbox.y2

            mean_depth = self._sample_depth(depth_norm, x1, y1, x2, y2)

            flags = []
            if mean_depth >= self.danger_threshold:
                flags.append('TOO_CLOSE')
            if label in self.unusual_objects:
                flags.append('UNUSUAL_OBJECT')

            if flags:
                self.get_logger().warn(
                    f"[ALERT] frame={frame_id} | {label} conf={conf:.2f} "
                    f"depth={mean_depth:.2f} flags={flags}"
                )
            else:
                self.get_logger().info(
                    f"frame={frame_id} | {label} conf={conf:.2f} "
                    f"depth={mean_depth:.2f} — OK"
                )

            # Build SceneObject (custom msg) for every detection, flagged or not
            obj = SceneObject()
            obj.class_name  = bbox.class_name
            obj.conf        = conf
            obj.x1          = x1
            obj.y1          = y1
            obj.x2          = x2
            obj.y2          = y2
            obj.mean_depth  = mean_depth
            obj.flags       = flags          # string[]

            flagged_objects.append(obj)

        # Publish even if nothing is flagged — downstream nodes decide what to act on
        out_msg = SceneAnalysis()
        out_msg.header  = header
        out_msg.objects = flagged_objects   # all detections with depth + flags attached

        self.publisher_.publish(out_msg)
        self.get_logger().info(
            f"Published /scene_analysis for frame {frame_id} "
            f"| {len(flagged_objects)} object(s)"
        )

    # -----------------------------------------------------------------------
    # Utility
    # -----------------------------------------------------------------------

    def _normalize_depth(self, depth_raw: np.ndarray) -> np.ndarray:
        """
        DepthAnythingV2 outputs relative disparity — no fixed metric scale.
        Normalize per-frame to [0, 1] where 1.0 = closest, 0.0 = farthest.
        """
        d_min, d_max = depth_raw.min(), depth_raw.max()
        if d_max > d_min:
            return (depth_raw - d_min) / (d_max - d_min)
        return np.zeros_like(depth_raw, dtype=np.float32)

    def _sample_depth(self, depth_norm: np.ndarray,
                      x1: int, y1: int, x2: int, y2: int) -> float:
        """
        Mean normalized depth inside a bounding box.
        Clamps coordinates to the depth map size (depth may be smaller than frame).
        """
        h, w = depth_norm.shape
        x1c, x2c = max(0, min(x1, w - 1)), max(0, min(x2, w))
        y1c, y2c = max(0, min(y1, h - 1)), max(0, min(y2, h))
        region = depth_norm[y1c:y2c, x1c:x2c]
        return float(np.mean(region)) if region.size > 0 else 0.0


def main(args=None):
    rclpy.init(args=args)
    node = SceneAnalysisNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down scene analysis node")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()