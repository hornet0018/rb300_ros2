#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # LiDAR用のLaunchConfiguration
    channel_type = LaunchConfiguration('channel_type', default='serial')
    serial_port = LaunchConfiguration('serial_port', default='/dev/rplidar_usb_serial')
    serial_baudrate = LaunchConfiguration('serial_baudrate', default='460800')
    frame_id = LaunchConfiguration('frame_id', default='laser')
    inverted = LaunchConfiguration('inverted', default='false')
    angle_compensate = LaunchConfiguration('angle_compensate', default='true')
    scan_mode = LaunchConfiguration('scan_mode', default='Standard')

    # シリアル送信ノード用のLaunchConfiguration
    esp32_serial_port = LaunchConfiguration('esp32_serial_port', default='/dev/esp32_usb_serial')
    wheel_radius = LaunchConfiguration('wheel_radius', default='0.085')
    wheel_separation = LaunchConfiguration('wheel_separation', default='0.1796')
    max_rpm = LaunchConfiguration('max_rpm', default='200')

    tf2_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        output='screen',
        arguments=['-0.042', '0', '0.1094', '-1.5708', '0','0','base_link','laser_frame'],
    )

    ros_tcp_endpoint_node = Node(
        package="ros_tcp_endpoint",
        executable="default_server_endpoint",
        emulate_tty=True,
        parameters=[{"ROS_IP": "0.0.0.0"}, {"ROS_TCP_PORT": 10000}],
    )

    return LaunchDescription([
        # LiDARの設定
        DeclareLaunchArgument(
            'channel_type',
            default_value=channel_type,
            description='Specifying channel type of lidar'),

        DeclareLaunchArgument(
            'serial_port',
            default_value=serial_port,
            description='Specifying usb port to connected lidar'),

        DeclareLaunchArgument(
            'serial_baudrate',
            default_value=serial_baudrate,
            description='Specifying usb port baudrate to connected lidar'),
        
        DeclareLaunchArgument(
            'frame_id',
            default_value=frame_id,
            description='Specifying frame_id of lidar'),

        DeclareLaunchArgument(
            'inverted',
            default_value=inverted,
            description='Specifying whether or not to invert scan data'),

        DeclareLaunchArgument(
            'angle_compensate',
            default_value=angle_compensate,
            description='Specifying whether or not to enable angle_compensate of scan data'),

        DeclareLaunchArgument(
            'scan_mode',
            default_value=scan_mode,
            description='Specifying scan mode of lidar'),

        # LiDARノード
        Node(
            package='sllidar_ros2',
            executable='sllidar_node',
            name='sllidar_node',
            parameters=[{
                'channel_type': channel_type,
                'serial_port': serial_port, 
                'serial_baudrate': serial_baudrate, 
                'frame_id': frame_id,
                'inverted': inverted, 
                'angle_compensate': angle_compensate, 
                'scan_mode': scan_mode
            }],
            output='screen'),

        # シリアル送信ノード
        Node(
            package='ros2_serial_communicator',
            executable='serial_sender',
            name='serial_sender',
            parameters=[{
                'serial_port': esp32_serial_port,
                'wheel_radius': wheel_radius,
                'wheel_separation': wheel_separation,
                'max_rpm': max_rpm,
            }],
            output='screen'),

        # tf2 ノード
        tf2_node,

        # ROS TCP Endpoint ノード
        ros_tcp_endpoint_node,
    ])
