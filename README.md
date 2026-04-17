# RB300 ROS2 Workspace

RB300ロボットプラットフォーム用のROS2ワークスペース

## 概要

このワークスペースには、RB300ロボットを制御・操作するためのROS2パッケージが含まれています。

## パッケージ構成

| パッケージ | 説明 |
|----------|------|
| [esp_serial_v2_cpp](esp_serial_v2_cpp/) | ESP32マイコンとのシリアル通信 |
| [rplidar_ros](rplidar_ros/) | RPLidar A1/A2/A3/S1/S2/S3/T1 用ドライバ |
| [camera_launch](camera_launch/) | USBカメラ起動ファイル（Hobot D-Robotics専用） |
| [rb300_launch](rb300_launch/) | RB300統合システム起動ファイル |
| [serial](serial/) | シリアル通信ライブラリ |

### 詳細

#### [esp_serial_v2_cpp](esp_serial_v2_cpp/)
ESP32マイコンとのシリアル通信を行うROS2ノード

- **機能**: ESP32からのシリアルデータをパースし、ROS2トピックとして配信
- **主な機能**:
  - シリアル通信によるデータ受信
  - JSON形式のデータパース
  - ダイアグノスト情報の配信
- **依存パッケージ**: rclcpp, nlohmann_json, serial, std_msgs, geometry_msgs, diagnostic_updater
- **ライセンス**: Apache License 2.0

#### [rplidar_ros](rplidar_ros/)
Slamtec RPLidarシリーズ用のROS2パッケージ

- **対応機種**: A1/A2/A3/S1/S2/S3/T1
- **機能**: LiDARセンサーからスキャンデータを取得し、`/scan`トピックとして配信
- **依存パッケージ**: rclcpp, sensor_msgs, std_srvs, rclcpp_components
- **ライセンス**: BSD

#### [camera_launch](camera_launch/)
USBカメラ用起動ファイルパッケージ

- **機能**: USBカメラの起動・設定を行うLaunchファイル（Hobot D-Robotics専用）
- **Launchファイル**:
  - `hobot_usb_cam.launch.py` - USBカメラの基本起動
  - `hobot_usb_cam_websocket.launch.py` - WebSocket経由でのストリーミング
  - `dnn_node_sample.launch.py` - DNN推論サンプル
- **依存パッケージ**: ros_base, diagnostic_updater, sensor_msgs, diagnostic_msgs, hobot_usb_cam, hobot_codec, hobot_shm

#### [rb300_launch](rb300_launch/)
RB300統合起動ファイルパッケージ

- **機能**: RB300ロボットの全ノードを一括起動
- **Launchファイル**:
  - `rb300_system.launch.py` - RPLidar + ESP32シリアルノードの統合起動

#### [serial](serial/)
シリアル通信ライブラリ（ROS2依存なし）

- **機能**: クロスプラットフォーム対応のシリアルポート通信ライブラリ
- **対応OS**: Linux, Windows
- **ライセンス**: MIT

## セットアップ

### ビルド

```bash
cd /home/sunrise/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### 依存関係のインストール

```bash
# ROS2パッケージの依存関係
sudo apt install ros-<ros2-distro>-diagnostic-updater
sudo apt install ros-<ros2-distro>-sensor-msgs
sudo apt install ros-<ros2-distro>-geometry-msgs
sudo apt install ros-<ros2-distro>-std-srvs

# nlohmann_json (システムパッケージ)
sudo apt install nlohmann-json3-dev
```

## 使用方法

### 全システムの起動（推奨）

RB300の全ノード（RPLidar + ESP32シリアル）を一括起動:

```bash
ros2 launch rb300_launch rb300_system.launch.py
```

パラメータを指定して起動:

```bash
ros2 launch rb300_launch rb300_system.launch.py \
  rplidar_serial_port:=/dev/ttyUSB0 \
  esp_serial_port:=/dev/esp32_serial
```

### 起動パラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| `rplidar_serial_port` | `/dev/ttyUSB0` | RPLidarのシリアルポート |
| `rplidar_baudrate` | `1000000` | RPLidarのボーレート |
| `rplidar_frame_id` | `laser` | RPLidarのフレームID |
| `rplidar_scan_mode` | `DenseBoost` | RPLidarのスキャンモード |
| `esp_serial_port` | `/dev/esp32_serial` | ESP32のシリアルポート |
| `esp_baud_rate` | `115200` | ESP32のボーレート |
| `wheel_radius` | `0.0473` | 車輪半径（m） |
| `wheel_separation` | `0.1796` | 車輪間隔（m） |
| `max_rpm` | `115` | 最大モーターRPM |
| `cmd_vel_timeout` | `0.5` | cmd_velタイムアウト（秒） |

### 個別ノードの起動

#### RPLidarの起動

```bash
ros2 launch rplidar_ros rplidar_s2_launch.py
```

#### ESP32シリアル通信ノードの起動

```bash
ros2 launch esp_serial_v2_cpp esp_serial.launch.py
```

#### USBカメラの起動

```bash
ros2 launch camera_launch hobot_usb_cam.launch.py
```

## トピック

| トピック名 | メッセージ型 | 説明 |
|------------|-------------|------|
| `/scan` | `sensor_msgs/LaserScan` | LiDARスキャンデータ |
| `/cmd_vel` | `geometry_msgs/Twist` | 速度指令 |
| `/odom` | `nav_msgs/Odometry` | オドメトリ |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | ダイアグノスト情報 |

## ハードウェア構成

- **LiDAR**: RPLidar A1/A2/A3/S1/S2/S3/T1
- **カメラ**: USBカメラ（UVC対応、Hobot D-Robotics対応）
- **マイコン**: ESP32（シリアル通信）

## ライセンス

各パッケージのライセンスに従ってください:
- esp_serial_v2_cpp: Apache License 2.0
- rplidar_ros: BSD
- serial: MIT

## 貢献

プルリクエストを歓迎します。
