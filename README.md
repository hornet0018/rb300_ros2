# RB300 ROS2 Workspace

RB300ロボットプラットフォーム用のROS2ワークスペース

## 概要

このワークスペースには、RB300ロボットを制御・操作するためのROS2パッケージが含まれています。

## 主な機能

- **LiDAR統合**: RPLidar C1によるスキャンデータ取得
- **オドメトリ生成**: エンコーダ値からの正確なオドメトリ計算
- **Web監視インターフェース**: ブラウザによるリアルタイム監視・操作
- **システムモニタリング**: CPU/メモリ使用率の表示

## パッケージ構成

| パッケージ | 説明 |
|----------|------|
| [esp_serial_v2_cpp](esp_serial_v2_cpp/) | ESP32マイコンとのシリアル通信 |
| [rplidar_ros](rplidar_ros/) | RPLidar ドライバ（git submodule） |
| [camera_launch](camera_launch/) | USBカメラ起動ファイル（Hobot D-Robotics専用） |
| [rb300_launch](rb300_launch/) | RB300統合システム（オドメトリ・Web監視） |
| [serial](serial/) | シリアル通信ライブラリ（git submodule） |

### 詳細

#### [rb300_launch](rb300_launch/)
RB300統合システムパッケージ

**ノード**:
- `odometry_publisher` - エンコーダ値からオドメトリを計算
- `system_monitor` - CPU/メモリ使用率を配信

**Launchファイル**:
- `rb300_system.launch.py` - 全システム統合起動
- `web_bridge.launch.py` - Webインターフェース用ブリッジ

**Webインターフェース**:
- リアルタイムオドメトリ表示
- エンコーダ値表示
- キャリブレーションコントロール
- システムリソース監視

#### [esp_serial_v2_cpp](esp_serial_v2_cpp/)
ESP32マイコンとのシリアル通信を行うROS2ノード

- **機能**: ESP32からのシリアルデータをパースし、ROS2トピックとして配信
- **主な機能**:
  - シリアル通信によるデータ受信
  - CBOR形式のデータパース
  - ダイアグノスト情報の配信
  - 速度指令の送信
- **ライセンス**: Apache License 2.0

#### [rplidar_ros](rplidar_ros/)
Slamtec RPLidarシリーズ用のROS2パッケージ（git submodule）

- **対応機種**: A1/A2/A3/C1/S1/S2/S2E/S3/T1
- **機能**: LiDARセンサーからスキャンデータを取得し、`/scan`トピックとして配信
- **ライセンス**: BSD

## セットアップ

### クローンとサブモジュールの取得

```bash
# リポジトリをクローン
git clone <repository-url>
cd rb300_ros2

# サブモジュールの初期化と最新の取得
git submodule update --init --recursive
```

### ビルド

```bash
cd /home/sunrise/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### 依存関係のインストール

```bash
# ROS2パッケージ
sudo apt install ros-humble-diagnostic-updater
sudo apt install ros-humble-rosbridge-suite

# システムパッケージ
sudo apt install nlohmann-json3-dev
```

## 使用方法

### 全システムの起動

```bash
ros2 launch rb300_launch rb300_system.launch.py
```

パラメータを指定して起動:

```bash
ros2 launch rb300_launch rb300_system.launch.py \
  rplidar_serial_port:=/dev/rplidar_c1 \
  esp_serial_port:=/dev/esp32_serial
```

### 起動パラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| **RPLidar** | | |
| `rplidar_serial_port` | `/dev/rplidar_c1` | RPLidarのシリアルポート |
| `rplidar_baudrate` | `460800` | RPLidarのボーレート |
| `rplidar_scan_mode` | `Standard` | RPLidarのスキャンモード |
| **ESP32シリアル** | | |
| `esp_serial_port` | `/dev/esp32_serial` | ESP32のシリアルポート |
| `esp_baud_rate` | `115200` | ESP32のボーレート |
| **ロボットパラメータ** | | |
| `wheel_radius` | `0.0473` | 車輪半径（m） |
| `wheel_separation` | `0.1796` | 車輪間隔（m） |
| `max_rpm` | `115` | 最大モーターRPM |
| `cmd_vel_timeout` | `0.5` | cmd_velタイムアウト（秒） |
| `invert_motor_l` | `true` | 左モーター反転 |
| `invert_motor_r` | `true` | 右モーター反転 |

### Webインターフェース

**端末1** - システム起動:
```bash
ros2 launch rb300_launch rb300_system.launch.py
```

**端末2** - Webブリッジ:
```bash
ros2 launch rb300_launch web_bridge.launch.py
```

**端末3** - HTTPサーバー:
```bash
cd /home/sunrise/ros2_ws/src/rb300_ros2/rb300_launch/web
python3 -m http.server 8000
```

ブラウザでアクセス:
```
http://localhost:8000/odom_viewer.html
```

**Web機能**:
- オドメトリ表示（X, Y, Theta）
- エンコーダ値表示（左/右車輪）
- システムリソース監視（CPU/メモリ）
- キャリブレーションボタン（前進1m、回転90°等）
- D-PADコントローラー

## トピック

### トピック一覧

| トピック名 | メッセージ型 | 説明 |
|------------|-------------|------|
| **オドメトリ** | | |
| `/odom` | `nav_msgs/Odometry` | オドメトリ |
| `/tf` | `tf2_msgs/TFMessage` | 座標変換（odom→base_link→laser） |
| **LiDAR** | | |
| `/scan` | `sensor_msgs/LaserScan` | LiDARスキャンデータ |
| **速度指令** | | |
| `/cmd_vel` | `geometry_msgs/Twist` | 速度指令 |
| **エンコーダ** | | |
| `/esp/position_l_rad` | `std_msgs/Float64` | 左車輪エンコーダ（rad） |
| `/esp/position_r_rad` | `std_msgs/Float64` | 右車輪エンコーダ（rad） |
| `/esp/speed_l` | `std_msgs/Int16` | 左車輪速度（RPM） |
| `/esp/speed_r` | `std_msgs/Int16` | 右車輪速度（RPM） |
| **システム監視** | | |
| `/system/cpu_usage` | `std_msgs/Float64` | CPU使用率（%） |
| `/system/memory_available_gb` | `std_msgs/Float64` | 空きメモリ（GB） |
| `/system/memory_usage_percent` | `std_msgs/Float64` | メモリ使用率（%） |
| **その他** | | |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | ダイアグノスト情報 |
| `/battery_voltage` | `std_msgs/Float32` | バッテリー電圧 |

### スクリプト

| スクリプト | 説明 |
|----------|------|
| `scripts/test_odom.py` | オドメトリテスト（0.1m/s × 10秒） |
| `scripts/monitor_odom.py` | オドメトリ監視（端末表示） |
| `scripts/analyze_odom.py` | rosbagオドメトリ解析 |
| `scripts/start_web.sh` | Webサーバー一括起動 |

## ハードウェア構成

| コンポーネント | モデル | 説明 |
|--------------|--------|------|
| **LiDAR** | RPLidar C1 | 2D LiDARスキャナー |
| **マイコン** | ESP32 | モーター制御・エンコーダ読み取り |
| **カメラ** | USB UVC | オプション（Hobot対応） |

## TFツリー

```
odom
 └── base_link
      ├── left_wheel_link
      ├── right_wheel_link
      └── laser
```

## ライセンス

各パッケージのライセンスに従ってください:
- rb300_launch: Apache License 2.0
- esp_serial_v2_cpp: Apache License 2.0
- rplidar_ros: BSD
- serial: MIT

## 貢献

プルリクエストを歓迎します。
