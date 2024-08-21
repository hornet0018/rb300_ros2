from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ros2_serial_communicator',
            executable='serial_sender',
            name='serial_sender',
            parameters=[{
                'serial_port': '/dev/esp32_usb_serial',
                'wheel_radius': 0.085,
                'wheel_separation': 0.1796,
                'max_rpm': 200,
            }]
        ),
    ])
