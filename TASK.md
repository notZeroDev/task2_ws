# Distributed Smart Security Surveillance System using ROS

## 1. Project Title

Distributed Smart Security Surveillance System using ROS

---

## 2. Project Overview

Design a distributed smart surveillance system using ROS.

The system analyzes a camera stream or video file to detect objects and monitor suspicious activity.

### System integrates:

- Camera streaming
- Object detection using YOLO
- Depth estimation using DepthAnythingV2
- Event detection
- Security response coordination

### System consists of:

8 nodes working together

### Input sources:

- Laptop camera
- Video files

No additional sensors or hardware are required.

---

## 3. Core Idea

The system continuously analyzes a video stream.

### Pipeline:

1. Camera captures frames
2. YOLO detects objects
3. Depth estimation estimates distance
4. Scene analyzer evaluates environment
5. Event manager identifies suspicious events
6. Security controller triggers responses
7. Logger records events
8. Monitor displays system status

All nodes communicate using ROS.

---

## 4. Required Nodes

### 4.1 Camera Stream Node

**Responsibility:**

- Capture frames from:
    - Laptop camera
    - Video file

**Publishes:**

- `/camera_frames`

**Subscribes:**

- None

**Parameters:**

- `camera_source`
- `frame_rate`

**Logic:**
Continuously capture frames and publish them.

---

### 4.2 Object Detection Node

**Responsibility:**

- Detect objects using YOLO

**Publishes:**

- `/detected_objects`

**Subscribes:**

- `/camera_frames`

**Parameters:**

- `confidence_threshold`
- `model_path`

**Logic:**
Run YOLO on each frame and publish bounding boxes.

---

### 4.3 Depth Estimation Node

**Responsibility:**

- Estimate object distance using DepthAnythingV2

**Publishes:**

- `/object_depth`

**Subscribes:**

- `/camera_frames`

**Parameters:**

- `depth_model_path`

**Logic:**
Generate depth map and estimate object distance.

---

### 4.4 Scene Analysis Node

**Responsibility:**

- Combine detection and depth information

**Publishes:**

- `/scene_analysis`

**Subscribes:**

- `/detected_objects`
- `/object_depth`

**Parameters:**

- `danger_distance`

**Logic:**
Identify objects that are too close or unusual.

---

### 4.5 Event Manager Node

**Responsibility:**

- Detect security events

**Publishes:**

- `/security_event`

**Subscribes:**

- `/scene_analysis`

**Parameters:**

- `restricted_objects`

**Logic:**
Identify events such as:

- Person in restricted area
- Object too close to camera

---

### 4.6 Security Response Node

**Responsibility:**

- Trigger response actions

**Publishes:**

- `/security_alert`

**Subscribes:**

- `/security_event`

**Actions Used:**

- `/security_action`

**Parameters:**

- `alert_level`

**Logic:**
Launch long-running response actions.

---

### 4.7 Event Logger Node

**Responsibility:**

- Record system activity

**Subscribes:**

- `/security_event`
- `/security_alert`

**Logic:**
Store events and print logs.

---

### 4.8 System Monitor Node

**Responsibility:**

- Observe system health

**Subscribes:**

- All main topics

**Logic:**
Display system status and performance.

---

## 5. System Rules

- Allowed inputs:
    - Webcam
    - Video files

- Detection frequency:
    - Minimum 5 FPS

- Depth estimation must run continuously

- System must detect at least two object types

---

## 6. Required ROS Communication

### Topics

| Topic             | Purpose           |
| ----------------- | ----------------- |
| /camera_frames    | Camera images     |
| /detected_objects | YOLO detection    |
| /object_depth     | Depth estimation  |
| /scene_analysis   | Combined analysis |
| /security_event   | Detected events   |
| /security_alert   | Triggered alerts  |

---

### Services

Optional services may be used for configuration.

---

### Actions

- `/security_action`  
  Used for long security responses.

---

### Parameters

Examples:

- Detection confidence
- Depth threshold
- Event thresholds

---

## 7. Main Objectives

Students must implement:

### A. Vision Pipeline

Process camera frames through multiple nodes.

### B. Multi-Node Coordination

Detection, depth, and decision nodes must cooperate.

### C. Action Communication

Security responses must use ROS actions.

### D. Parameter Configuration

System behavior must be adjustable using ROS parameters.

### E. Debugging Distributed Systems

Ensure reliable message flow.

---

## 8. Team Division (Mandatory)

| Student   | Node              |
| --------- | ----------------- |
| Student 1 | Camera Stream     |
| Student 2 | Object Detection  |
| Student 3 | Depth Estimation  |
| Student 4 | Scene Analysis    |
| Student 5 | Event Manager     |
| Student 6 | Security Response |
| Student 7 | Event Logger      |
| Student 8 | System Monitor    |

---

## 9. Execution Method

### ROS1

    roscore

    rosrun your_package camera_stream
    rosrun your_package object_detector
    rosrun your_package depth_estimator
    rosrun your_package scene_analyzer
    rosrun your_package event_manager
    rosrun your_package security_response
    rosrun your_package event_logger
    rosrun your_package system_monitor

### ROS2

    ros2 run your_package camera_stream
    ros2 run your_package object_detector
    ros2 run your_package depth_estimator
    ros2 run your_package scene_analyzer
    ros2 run your_package event_manager
    ros2 run your_package security_response
    ros2 run your_package event_logger
    ros2 run your_package system_monitor

---

## 10. Submission Requirements

Teams must submit:

1. Source code
2. Running demonstration video + achieved output
3. Explanation of each node

Each student must explain:

- Node logic
- ROS communication used
- System integration

Students must also mention ROS1 vs ROS2 differences.
