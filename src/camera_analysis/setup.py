from setuptools import find_packages, setup

package_name = 'camera_analysis'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'opencv-python', 'cv-bridge'],
    zip_safe=True,
    maintainer='zero',
    maintainer_email='mohmed.ayman11@gmail.com',
    description='Camera analysis package with video/camera streaming to ROS 2 topics',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'camera_node=camera_analysis.camera_node:main',
        ],
    },
)
