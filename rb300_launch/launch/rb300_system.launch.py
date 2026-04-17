#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python import get_package_share_directory


def generate_launch_description():
    # RPLidar Launch
    rplidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('rplidar_ros'),
                'launch/rplidar_s2_launch.py'))
        ),
        launch_arguments={
            'serial_port': LaunchConfiguration('rplidar_serial_port'),
            'serial_baudrate': LaunchConfiguration('rplidar_baudrate'),
            'frame_id': LaunchConfiguration('rplidar_frame_id'),
            'inverted': LaunchConfiguration('rplidar_inverted'),
            'angle_compensate': LaunchConfiguration('rplidar_angle_compensate'),
            'scan_mode': LaunchConfiguration('rplidar_scan_mode'),
        }.items()
    )

    # ESP Serial Launch
    esp_serial_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('esp_serial_v2_cpp'),
                'launch/esp_serial_launch.py'))
        ),
        launch_arguments={
            'serial_port': LaunchConfiguration('esp_serial_port'),
            'baud_rate': LaunchConfiguration('esp_baud_rate'),
            'wheel_radius': LaunchConfiguration('wheel_radius'),
            'wheel_separation': LaunchConfiguration('wheel_separation'),
            'max_rpm': LaunchConfiguration('max_rpm'),
            'update_rate': LaunchConfiguration('update_rate'),
            'cmd_vel_timeout': LaunchConfiguration('cmd_vel_timeout'),
            'invert_motor_l': LaunchConfiguration('invert_motor_l'),
            'invert_motor_r': LaunchConfiguration('invert_motor_r'),
        }.items()
    )

    return LaunchDescription([
        # RPLidar Arguments
        DeclareLaunchArgument(
            'rplidar_serial_port',
            default_value='/dev/ttyUSB0',
            description='Serial port for RPLidar'
        ),
        DeclareLaunchArgument(
            'rplidar_baudrate',
            default_value='1000000',
            description='Baud rate for RPLidar'
        ),
        DeclareLaunchArgument(
            'rplidar_frame_id',
            default_value='laser',
            description='Frame ID for RPLidar'
        ),
        DeclareLaunchArgument(
            'rplidar_inverted',
            default_value='false',
            description='Invert RPLidar scan data'
        ),
        DeclareLaunchArgument(
            'rplidar_angle_compensate',
            default_value='true',
            description='Enable angle compensation'
        ),
        DeclareLaunchArgument(
            'rplidar_scan_mode',
            default_value='DenseBoost',
            description='RPLidar scan mode'
        ),

        # ESP Serial Arguments
        DeclareLaunchArgument(
            'esp_serial_port',
            default_value='/dev/esp32_serial',
            description='Serial port for ESP32'
        ),
        DeclareLaunchArgument(
            'esp_baud_rate',
            default_value='115200',
            description='Baud rate for ESP32'
        ),
        DeclareLaunchArgument(
            'wheel_radius',
            default_value='0.0473',
            description='Wheel radius in meters'
        ),
        DeclareLaunchArgument(
            'wheel_separation',
            default_value='0.1796',
            description='Wheel separation in meters'
        ),
        DeclareLaunchArgument(
            'max_rpm',
            default_value='115',
            description='Maximum motor RPM'
        ),
        DeclareLaunchArgument(
            'update_rate',
            default_value='100.0',
            description='Serial read rate in Hz'
        ),
        DeclareLaunchArgument(
            'cmd_vel_timeout',
            default_value='0.5',
            description='Timeout for cmd_vel in seconds'
        ),
        DeclareLaunchArgument(
            'invert_motor_l',
            default_value='true',
            description='Invert left motor rotation'
        ),
        DeclareLaunchArgument(
            'invert_motor_r',
            default_value='true',
            description='Invert right motor rotation'
        ),

        # Launch nodes
        rplidar_launch,
        esp_serial_launch,
    ])
