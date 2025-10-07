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
    frame_id = LaunchConfiguration('frame_id', default='laser_frame')
    inverted = LaunchConfiguration('inverted', default='false')
    angle_compensate = LaunchConfiguration('angle_compensate', default='true')
    scan_mode = LaunchConfiguration('scan_mode', default='Standard')

    # シリアル送信ノード用のLaunchConfiguration
    esp32_serial_port = LaunchConfiguration('esp32_serial_port', default='/dev/esp32_usb_serial')
    wheel_radius = LaunchConfiguration('wheel_radius', default='0.0473')
    wheel_separation = LaunchConfiguration('wheel_separation', default='0.205')
    max_rpm = LaunchConfiguration('max_rpm', default='200')

    # map → odom の変換
    map_to_odom = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_odom',
        arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0',
                   '--frame-id', 'map', '--child-frame-id', 'odom']
    )

    # base_footprint → base_link の変換
    base_footprint_to_base_link = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_footprint_to_base_link',
        arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0425', 
                   '--frame-id', 'base_footprint', '--child-frame-id', 'base_link']
    )

    # base_link → laser_frame の変換（180度回転）
    base_link_to_laser_frame = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_laser_frame',
        arguments=['--x', '0.0', '--y', '0.0', '--z', '0.0975',  # 0.142 - 0.0425 = 0.0975
                '--roll', '0.0', '--pitch', '0.0', '--yaw', '3.14159',  # 180度回転
                '--frame-id', 'base_link', '--child-frame-id', 'laser_frame']
    )

    # SLAM ノード
    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        output='screen',
        parameters=[
            get_package_share_directory('ros2_serial_communicator')
            + '/configuration_files/mapper_params_offline.yaml'
        ],
    )

    # RViz2 ノード
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=[
            '-d',
            get_package_share_directory('ros2_serial_communicator')
            + '/config/gmapping.rviz'
        ],
    )

    # ROS TCP Endpoint ノード
    ros_tcp_endpoint_node = Node(
        package="ros_tcp_endpoint",
        executable="default_server_endpoint",
        emulate_tty=True,
        parameters=[{"ROS_IP": "0.0.0.0"}, {"ROS_TCP_PORT": 10000}],
    )

    return LaunchDescription([
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

        # TF変換ノード
        base_footprint_to_base_link,
        base_link_to_laser_frame,
        map_to_odom,
        
        # SLAM ノード
        slam_node,

        # RViz2 ノード
        rviz2_node,

        # ROS TCP Endpoint ノード
        ros_tcp_endpoint_node,
    ])
