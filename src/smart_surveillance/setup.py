from setuptools import find_packages, setup

package_name = 'smart_surveillance'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ahmed',
    maintainer_email='ahmed@todo.todo',
    description='Distributed Smart Security Surveillance System',
    license='MIT',
    entry_points={
        'console_scripts': [
            'camera_stream     = smart_surveillance.camera_streamer_node:main',
            'object_detector   = smart_surveillance.object_detector_node:main',
            'depth_estimator   = smart_surveillance.depth_estimator_node:main',
            'scene_analyzer    = smart_surveillance.scene_analyzer_node:main',
            'event_manager     = smart_surveillance.event_manager_node:main',
            'security_response = smart_surveillance.security_response_node:main',
            'event_logger      = smart_surveillance.event_logger_node:main',
            'system_monitor    = smart_surveillance.system_monitor_node:main',
        ],
    },
)
