# RB300 ROS2 Workspace

RB300ロボットプラットフォーム用のROS2ワークスペース(ROS2 Humble / arm64)

## 概要

このワークスペースには、RB300ロボットを制御・操作するためのROS2パッケージが含まれています。
GitHub Actions の arm64 ランナーでビルドし、install 空間を単一の tar.gz + sha256 マニフェストとして配布できます。

## 主な機能

- **LiDAR統合**: RPLidar C1によるスキャンデータ取得
- **オドメトリ生成**: エンコーダ値からの正確なオドメトリ計算(キャリブレーションYAML対応)
- **SLAM**: slam_toolboxベースの自己位置推定(`rb300_nav`)
- **Web UI**: ブラウザベースの監視・操作(`rb300_webui`、rosbridge + HTTPサーバー)
- **システムモニタリング**: CPU/メモリ使用率の表示

## パッケージ構成

| パッケージ | 説明 |
|----------|------|
| [esp_serial_v2_cpp](esp_serial_v2_cpp/) | ESP32マイコンとのシリアル通信 + オドメトリ計算(git submodule) |
| [rplidar_ros](rplidar_ros/) | RPLidar ドライバ(git submodule) |
| [rb300_webui](rb300_webui/) | RB300統合システム(全ノード起動・Web UI)(git submodule) |
| [rb300_nav](rb300_nav/) | SLAM(自己位置推定)制御(git submodule) |
| [serial](serial/) | シリアル通信ライブラリ(git submodule) |

### 詳細

#### [rb300_webui](rb300_webui/)
RB300統合システムパッケージ

**Launchファイル**:
- `rb300_all.launch.py` - 全システム + Web UI(rosbridge + HTTPサーバー)統合起動
- `rb300_system.launch.py` - ロボット制御系のみ(RPLidar + ESP32 + オドメトリ + SLAM)
- `web_bridge.launch.py` - rosbridge WebSocketのみ

**ノード**:
- `system_monitor` - CPU/メモリ使用率を配信

#### [esp_serial_v2_cpp](esp_serial_v2_cpp/)
ESP32マイコンとのシリアル通信を行うROS2ノード

- **ノード**:
  - `esp_serial_ros2` - ESP32からのシリアルデータをパースし、ROS2トピックとして配信
  - `odometry_publisher` - エンコーダ値からオドメトリを計算
- **キャリブレーション**: `config/odometry_calibration.yaml` で車輪半径・車輪間隔などを設定
- **ライセンス**: Apache License 2.0

#### [rb300_nav](rb300_nav/)
SLAM制御パッケージ

- **ノード**: `slam_controller.py` - `/rb300_webui/slam_command` を監視し slam_toolbox を制御
- **Launchファイル**: `slam.launch.py` / 設定: `config/slam_toolbox.yaml`
- **ライセンス**: MIT

#### [rplidar_ros](rplidar_ros/)
Slamtec RPLidarシリーズ用のROS2パッケージ(git submodule)

- **対応機種**: A1/A2/A3/C1/S1/S2/S2E/S3/T1
- **機能**: LiDARセンサーからスキャンデータを取得し、`/scan`トピックとして配信
- **ライセンス**: BSD

## セットアップ

### クローンとサブモジュールの取得

```bash
git clone <repository-url>
cd rb300_ros2
git submodule update --init --recursive
```

### 依存関係のインストール

```bash
# ROS2パッケージ
sudo apt install ros-humble-diagnostic-updater
sudo apt install ros-humble-rosbridge-suite
sudo apt install ros-humble-robot-state-publisher
sudo apt install ros-humble-slam-toolbox

# システムパッケージ
sudo apt install nlohmann-json3-dev
```

### ローカルビルド

```bash
cd /home/sunrise/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## CIビルド (GitHub Actions / arm64)

`.github/workflows/build-arm64.yml` が arm64 ランナー(`ubuntu-22.04-arm`、**公開リポジトリ限定**)でビルドします。

**実行内容**:
1. ROS2 Humble を arm64 にインストール
2. `colcon build --merge-install -DCMAKE_BUILD_TYPE=Release` で全パッケージを単一install空間にビルド
3. install空間を `rb300_arm64.tar.gz` に圧縮し、`rb300_manifest.json`(version / arch / git_commit / **sha256**)を生成
4. `v*`タグpush → GitHub Release に tar + manifest を添付 / それ以外 → Actions アーティファクトに保存
5. (任意) `GPG_PRIVATE_KEY` secret 設定時は manifest に署名(`.asc`)を付与

**トリガー**: `main` への push / `v*` タグ push / 手動(workflow_dispatch、`runner`入力でランナー変更可)

**Release 版の作成**:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## デプロイ (OTA / A/B差し替え)

ロボット側で `deploy/` のスクリプトを使い、Releaseからダウンロード→検証→`/opt/app/rb300/ver-<hash>` に展開→`current` シンボリックリンク差し替え→サービス再起動を行います。旧バージョンは最大3世代保持され、ロールバック可能です。

### 初回セットアップ

```bash
sudo ./deploy/setup_rb300.sh   # start.sh 配置 + rb300.service をsystemdに登録・有効化
```

### 更新

```bash
sudo ./deploy/update_rb300.sh            # 最新Releaseを適用
sudo ./deploy/update_rb300.sh v0.1.0     # 特定バージョンを適用
sudo ./deploy/update_rb300.sh --rollback # 前バージョンへ切り替え
```

**環境変数(上書き可)**:
| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `RB300_REPO` | `hornet0018/rb300_ros2` | GitHubリポジトリ |
| `RB300_TARGET` | `/opt/app/rb300` | インストール先 |
| `RB300_KEEP` | `3` | 保持する旧バージョン数 |
| `RB300_DOWNLOAD` | (未設定) | ダウンロードURLの上書き(ミラー/S3等) |
| `RB300_GPG_KEY` | (未設定) | manifestのGPG署名検証用フィンガープリント |

**systemdサービス** (`deploy/rb300.service`): `/opt/app/rb300/start.sh` を起動。`start.sh` は `/opt/ros/humble/setup.bash` と `current/install/setup.bash` をsourceして `ros2 launch rb300_webui rb300_system.launch.py` を実行します。

## 使用方法

### 全システム + Web UI の起動(推奨)

```bash
ros2 launch rb300_webui rb300_all.launch.py
```

ブラウザでアクセス:
```
http://<robot_ip>:8080/
```

### ロボット制御系のみの起動

```bash
ros2 launch rb300_webui rb300_system.launch.py
```

パラメータを指定して起動:

```bash
ros2 launch rb300_webui rb300_all.launch.py \
  rplidar_serial_port:=/dev/rplidar_serial \
  esp_serial_port:=/dev/esp32_serial
```

### rosbridge WebSocket のみ

```bash
ros2 launch rb300_webui web_bridge.launch.py
```

### 起動パラメータ

| パラメータ | デフォルト値 | 説明 |
|----------|------------|------|
| **RPLidar** | | |
| `rplidar_serial_port` | `/dev/rplidar_serial` | RPLidarのシリアルポート |
| `rplidar_baudrate` | `460800` | RPLidarのボーレート |
| `rplidar_frame_id` | `laser` | RPLidarのフレームID |
| `rplidar_inverted` | `false` | スキャンデータ反転 |
| `rplidar_angle_compensate` | `true` | 角度補正有効 |
| `rplidar_scan_mode` | `Standard` | RPLidarのスキャンモード |
| `rplidar_flip_x_axis` | `true` | X軸反転 |
| **ESP32シリアル** | | |
| `esp_serial_port` | `/dev/esp32_serial` | ESP32のシリアルポート |
| `esp_baud_rate` | `115200` | ESP32のボーレート |
| `max_rpm` | `115` | 最大モーターRPM |
| `update_rate` | `50.0` | シリアル読み取りレート(Hz) |
| `pulses_per_rev` | `32767.0` | エンコーダ1回転のパルス数 |
| `cmd_vel_timeout` | `0.5` | cmd_velタイムアウト(秒) |
| `invert_motor_l` | `true` | 左モーター反転 |
| `invert_motor_r` | `true` | 右モーター反転 |
| **Web UI** | | |
| `rosbridge_port` | `9090` | rosbridge WebSocketポート |
| `rosbridge_address` | `` | WebSocketバインドアドレス(空=全IF) |
| `rosbridge_delay` | `3` | rosbridge起動遅延(秒) |
| `web_port` | `8080` | HTTPサーバーポート(`web_dev:=false`時) |
| `web_dev` | `false` | Vite開発サーバーを使用 |

> オドメトリのキャリブレーション(車輪半径など)は `esp_serial_v2_cpp/config/odometry_calibration.yaml` で設定します。

## トピック

### トピック一覧

| トピック名 | メッセージ型 | 説明 |
|------------|-------------|------|
| **オドメトリ** | | |
| `/odom` | `nav_msgs/Odometry` | オドメトリ |
| `/tf` | `tf2_msgs/TFMessage` | 座標変換(odom→base_link→laser) |
| **LiDAR** | | |
| `/scan` | `sensor_msgs/LaserScan` | LiDARスキャンデータ |
| **速度指令** | | |
| `/cmd_vel` | `geometry_msgs/Twist` | 速度指令 |
| **エンコーダ** | | |
| `/esp/position_l_rad` | `std_msgs/Float64` | 左車輪エンコーダ(rad) |
| `/esp/position_r_rad` | `std_msgs/Float64` | 右車輪エンコーダ(rad) |
| `/esp/speed_l` | `std_msgs/Int16` | 左車輪速度(RPM) |
| `/esp/speed_r` | `std_msgs/Int16` | 右車輪速度(RPM) |
| **システム監視** | | |
| `/system/cpu_usage` | `std_msgs/Float64` | CPU使用率(%) |
| `/system/memory_available_gb` | `std_msgs/Float64` | 空きメモリ(GB) |
| `/system/memory_usage_percent` | `std_msgs/Float64` | メモリ使用率(%) |
| **その他** | | |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | ダイアグノスト情報 |
| `/battery_voltage` | `std_msgs/Float32` | バッテリー電圧 |
| `/rb300_webui/slam_command` | `std_msgs/String` | SLAMコマンド(Web UI経由) |

### スクリプト

| スクリプト | 説明 |
|----------|------|
| `scripts/test_odom.py` | オドメトリテスト(0.1m/s × 10秒) |
| `scripts/monitor_odom.py` | オドメトリ監視(端末表示) |
| `scripts/analyze_odom.py` | rosbagオドメトリ解析 |
| `deploy/setup_rb300.sh` | 初回デプロイセットアップ |
| `deploy/update_rb300.sh` | OTA更新・ロールバック |
| `deploy/start.sh` | systemd用起動スクリプト |
| `deploy/rb300.service` | systemdユニット定義 |

## ハードウェア構成

| コンポーネント | モデル | 説明 |
|--------------|--------|------|
| **LiDAR** | RPLidar C1 | 2D LiDARスキャナー |
| **マイコン** | ESP32 | モーター制御・エンコーダ読み取り |
| **カメラ** | USB UVC | オプション(Hobot対応) |

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
- esp_serial_v2_cpp: Apache License 2.0
- rb300_nav: MIT
- rplidar_ros: BSD
- serial: MIT
- rb300_webui: package.xml に記載なし(要確認)

## 貢献

プルリクエストを歓迎します。
