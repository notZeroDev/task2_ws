# Distributed Smart Security Surveillance System

A ROS 2 Python package implementing a distributed surveillance pipeline using computer vision and machine learning.

## System Overview

8 nodes work together to analyze a video stream for security events:

| Node | Topic(s) | Description |
|---|---|---|
| `camera_stream` | → `/camera_frames` | Captures frames from webcam or video file |
| `object_detector` | ← `/camera_frames` → `/detected_objects` | YOLO object detection |
| `depth_estimator` | ← `/camera_frames` → `/object_depth` | Monocular depth estimation (DepthAnythingV2) |
| `scene_analyzer` | ← `/detected_objects`, `/object_depth` → `/scene_analysis` | Combines detection + depth |
| `event_manager` | ← `/scene_analysis` → `/security_event` | Identifies security events |
| `security_response` | ← `/security_event` → `/security_alert` | Triggers response actions |
| `event_logger` | ← `/security_event`, `/security_alert` | Logs all activity |
| `system_monitor` | ← all topics | Displays system health |

---

## First-Time Setup

### 1. Install Python dependencies

```bash
pip3 install ultralytics timm
```

### 2. Download DepthAnythingV2 (for depth estimator node)

```bash
# Clone the DepthAnythingV2 repo into the workspace root
git clone https://github.com/DepthAnything/Depth-Anything-V2 /root/task2_ws/Depth-Anything-V2

# Download the ViT-Small weights (~100MB)
mkdir -p /root/task2_ws/checkpoints
wget -O /root/task2_ws/checkpoints/depth_anything_v2_vits.pth \
  https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/main/depth_anything_v2_vits.pth
```

> **Note:** `Depth-Anything-V2/`, `checkpoints/`, and `*.pt`/`*.pth` files are gitignored. Every teammate must run the above steps on first clone.

### 3. Build the workspace

```bash
cd /root/task2_ws
colcon build --packages-select surveillance_system
source install/setup.bash
```

---

## Running the System

Each node runs in its own terminal. Source the workspace first in each:

```bash
source /root/task2_ws/install/setup.bash
```

### Node 1 — Camera Stream

```bash
# From webcam (device 0)
ros2 run surveillance_system camera_stream

# From video file
ros2 run surveillance_system camera_stream --ros-args \
  -p camera_source:=/root/task2_ws/data/video.mp4 \
  -p frame_rate:=30.0
```

**Parameters:**
- `camera_source` — device index (default `0`) or path to video file
- `frame_rate` — FPS (default `30.0`)

---

### Node 2 — Object Detector

```bash
ros2 run surveillance_system object_detector
```

**Parameters:**
- `model_path` — YOLO model file (default `yolov8n.pt`, auto-downloaded on first run)
- `confidence_threshold` — detection confidence cutoff (default `0.5`)

---

### Node 3 — Depth Estimator

```bash
ros2 run surveillance_system depth_estimator
```

**Parameters:**
- `depth_model_path` — path to `.pth` weights (default `/root/task2_ws/checkpoints/depth_anything_v2_vits.pth`)
- `encoder` — model variant: `vits`, `vitb`, `vitl` (default `vits`)
- `process_every_n` — process 1 in every N frames for CPU efficiency (default `3`)
- `near_threshold` — normalized depth above which a region is "near" (default `0.65`)
- `input_size` — inference resolution in pixels (default `392`)

---

## Topics Reference

| Topic | Type | Publisher | Subscribers |
|---|---|---|---|
| `/camera_frames` | `sensor_msgs/Image` | camera_stream | object_detector, depth_estimator |
| `/detected_objects` | `std_msgs/String` | object_detector | scene_analyzer |
| `/object_depth` | `std_msgs/String` | depth_estimator | scene_analyzer |
| `/scene_analysis` | `std_msgs/String` | scene_analyzer | event_manager |
| `/security_event` | `std_msgs/String` | event_manager | security_response, event_logger |
| `/security_alert` | `std_msgs/String` | security_response | event_logger |

### Message Formats

**`/detected_objects`**
```
car 0.91 [382,323,788,471]; person 0.86 [67,262,183,602]; ...
```
Format: `<label> <confidence> [x1,y1,x2,y2]` separated by `; `

**`/object_depth`**
```
frame_id=42; avg_depth=0.32; near_ratio=0.23; min=0.00; max=7.54
```
- `frame_id` — monotonic counter of processed depth frames (increments every `process_every_n` frames)
- `avg_depth` — mean normalized depth (0=far, 1=near)
- `near_ratio` — fraction of frame pixels above `near_threshold`
- `min`/`max` — raw depth map value range
