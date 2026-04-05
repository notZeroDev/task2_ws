# Camera Analysis Package

A ROS 2 Python package for streaming video or camera frames using OpenCV to the `/camera_frames` topic.

## Installation

```bash
cd ~/ros2_ws
colcon build --packages-select camera_analysis
source install/setup.bash
```

## Running

**Default (camera device 0 at 30 FPS):**
```bash
ros2 run camera_analysis camera_node
```

**With parameters:**
```bash
ros2 run camera_analysis camera_node --ros-args -p camera_source:=0 -p frame_rate:=30
```

**From video file:**
```bash
ros2 run camera_analysis camera_node --ros-args -p camera_source:="/path/to/video.mp4"
```

## Parameters

- `camera_source`: Camera device ID (default: `0`) or path to video file
- `frame_rate`: Frame rate in FPS (default: `30`)

## Topic

Publishes `sensor_msgs/Image` messages to `/camera_frames`
