import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    params_file = LaunchConfiguration('params_file')
    map_yaml_file = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')

    declare_map_yaml = DeclareLaunchArgument(
        'map',
        default_value='',
        description='Full path to map yaml file to load')
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true')
    declare_params_file = DeclareLaunchArgument(
        'params_file',
        default_value=[
            TextSubstitution(text=os.path.join(
                get_package_share_directory('emcl2'), 'config', '')),
            TextSubstitution(text='emcl2.param.yaml')],
        description='emcl2 param file path')

    # RViz 用設定
    rviz_config_dir = os.path.join(
        get_package_share_directory('rb300_navigation'),
        'rviz',
        'tb3_navigation2.rviz'
    )

    # --- LiDAR 用 LaunchConfiguration と引数宣言 ---
    channel_type   = LaunchConfiguration('channel_type',   default='serial')
    serial_port    = LaunchConfiguration('serial_port',    default='/dev/rplidar_usb_serial')
    serial_baudrate= LaunchConfiguration('serial_baudrate',default='460800')
    frame_id       = LaunchConfiguration('frame_id',       default='laser_frame')
    inverted       = LaunchConfiguration('inverted',       default='false')
    angle_compensate = LaunchConfiguration('angle_compensate', default='true')
    scan_mode      = LaunchConfiguration('scan_mode',      default='Standard')

    declare_channel_type = DeclareLaunchArgument(
        'channel_type', default_value=channel_type,
        description='Specifying channel type of lidar')
    declare_serial_port = DeclareLaunchArgument(
        'serial_port', default_value=serial_port,
        description='Specifying usb port to connected lidar')
    declare_serial_baudrate = DeclareLaunchArgument(
        'serial_baudrate', default_value=serial_baudrate,
        description='Specifying usb port baudrate to connected lidar')
    declare_frame_id = DeclareLaunchArgument(
        'frame_id', default_value=frame_id,
        description='Specifying frame_id of lidar')
    declare_inverted = DeclareLaunchArgument(
        'inverted', default_value=inverted,
        description='Specifying whether or not to invert scan data')
    declare_angle_compensate = DeclareLaunchArgument(
        'angle_compensate', default_value=angle_compensate,
        description='Specifying whether or not to enable angle_compensate of scan data')
    declare_scan_mode = DeclareLaunchArgument(
        'scan_mode', default_value=scan_mode,
        description='Specifying scan mode of lidar')

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


    # map→odom の static TF
    map_static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher',
        output='log',
        arguments=[
            '0.0', '0.0', '0.0',  # x y z 
            '0.0', '0.0', '0.0',  # roll pitch yaw
            'map', 'odom'
        ]
    )

        # ROS TCP Endpoint ノード
    ros_tcp_endpoint_node = Node(
        package="ros_tcp_endpoint",
        executable="default_server_endpoint",
        emulate_tty=True,
        parameters=[{"ROS_IP": "0.0.0.0"}, {"ROS_TCP_PORT": 10000}],
    )

    lifecycle_nodes = ['map_server']

    launch_node = GroupAction(
        actions=[
            SetParameter('use_sim_time', use_sim_time),
            # LiDAR ノード
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
                output='screen'),
            # 既存ノード群…
            map_static_tf_node,
            base_footprint_to_base_link,
            base_link_to_laser_frame,
            ros_tcp_endpoint_node,
            Node(
                package='nav2_map_server',
                executable='map_server',
                name='map_server',
                parameters=[{'yaml_filename': map_yaml_file}],
                output='screen'),
            Node(
                name='emcl2',
                package='emcl2',
                executable='emcl2_node',
                parameters=[params_file],
                output='screen'),
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_localization',
                output='screen',
                parameters=[{'autostart': True},
                            {'node_names': lifecycle_nodes}]
            ),
            # RViz
            Node(
                package='rviz2',
                executable='rviz2',
                name='rviz2',
                arguments=['-d', rviz_config_dir],
                parameters=[{'use_sim_time': use_sim_time}],
                output='screen'
            ),
        ]
    )

    ld = LaunchDescription()
    # 既存引数
    ld.add_action(declare_map_yaml)
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_params_file)
    # LiDAR 引数
    ld.add_action(declare_channel_type)
    ld.add_action(declare_serial_port)
    ld.add_action(declare_serial_baudrate)
    ld.add_action(declare_frame_id)
    ld.add_action(declare_inverted)
    ld.add_action(declare_angle_compensate)
    ld.add_action(declare_scan_mode)
    # ノード群
    ld.add_action(launch_node)

    return ld
