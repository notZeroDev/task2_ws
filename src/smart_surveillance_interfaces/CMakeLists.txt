cmake_minimum_required(VERSION 3.8)
project(smart_surveillance_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/DetectedObjects.msg"
  "msg/ObjectDepth.msg"
  "msg/SceneAnalysis.msg"
  "msg/SecurityEvent.msg"
  "msg/SecurityAlert.msg"
  "action/SecurityAction.action"
  DEPENDENCIES std_msgs sensor_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
