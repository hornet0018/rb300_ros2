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
    serial_port = LaunchConfiguration('serial_port', default='/dev/ttyUSB0')
    serial_baudrate = LaunchConfiguration('serial_baudrate', default='460800')
    frame_id = LaunchConfiguration('frame_id', default='laser_frame')
    inverted = LaunchConfiguration('inverted', default='false')
    angle_compensate = LaunchConfiguration('angle_compensate', default='true')
    scan_mode = LaunchConfiguration('scan_mode', default='Standard')

    # シリアル送信ノード用のLaunchConfiguration
    esp32_serial_port = LaunchConfiguration('esp32_serial_port', default='/dev/ttyUSB1')
    wheel_radius = LaunchConfiguration('wheel_radius', default='0.085')
    wheel_separation = LaunchConfiguration('wheel_separation', default='0.1796')
    max_rpm = LaunchConfiguration('max_rpm', default='200')

    ros_tcp_endpoint_node = Node(
        package="ros_tcp_endpoint",
        executable="default_server_endpoint",
        emulate_tty=True,
        parameters=[{"ROS_IP": "0.0.0.0"}, {"ROS_TCP_PORT": 10000}],
    )

    # base_link から laser_frame への静的変換
    tf2_node_laser = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub_laser',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'base_link', 'laser_frame'],
    )

    # map から odom への静的変換
    tf2_node_map_to_odom = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub_map_to_odom',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'map', 'odom'],
    )

    # odom から base_footprint への静的変換
    tf2_node_odom_to_base_footprint = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub_odom_to_base_footprint',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'odom', 'base_footprint'],
    )

    # base_footprint から base_link への静的変換
    tf2_node_base_footprint_to_base_link = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub_base_footprint_to_base_link',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'base_footprint', 'base_link'],
    )

    slam_node = Node(
        package='slam_toolbox',
        executable='sync_slam_toolbox_node',
        output='screen',
        parameters=[
            get_package_share_directory('ros2_serial_communicator')
            + '/configuration_files/mapper_params_offline.yaml'
        ],
    )

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

        # ROS TCP Endpoint ノード
        ros_tcp_endpoint_node,

        # TF2 ノードの追加
        tf2_node_laser,
        tf2_node_map_to_odom,
        tf2_node_odom_to_base_footprint,
        tf2_node_base_footprint_to_base_link,

        # SLAM ノードの追加
        slam_node,

        # RViz2 ノードの追加
        rviz2_node,
    ])
