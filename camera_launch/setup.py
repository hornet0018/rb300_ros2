from setuptools import setup
import os
from glob import glob

package_name = 'camera_launch'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='User',
    maintainer_email='user@example.com',
    description='Launch file for USB camera',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'rplidar_diagnostic_node = camera_launch.rplidar_diagnostic_node:main',
        ],
    },
)
