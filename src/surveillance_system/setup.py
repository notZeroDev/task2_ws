from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'surveillance_system'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Team',
    maintainer_email='team@todo.todo',
    description='Distributed Smart Security Surveillance System using ROS 2',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'camera_stream = surveillance_system.nodes.camera_stream_node:main',
            'object_detector = surveillance_system.nodes.object_detector_node:main',
            'depth_estimator = surveillance_system.nodes.depth_estimator_node:main',
            'scene_analyzer = surveillance_system.nodes.scene_analyzer_node:main',
            'event_manager = surveillance_system.nodes.event_manager_node:main',
            'security_response = surveillance_system.nodes.security_response_node:main',
            'event_logger = surveillance_system.nodes.event_logger_node:main',
            'system_monitor = surveillance_system.nodes.system_monitor_node:main',
        ],
    },
)
