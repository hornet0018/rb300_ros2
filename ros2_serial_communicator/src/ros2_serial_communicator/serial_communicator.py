import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Quaternion, TransformStamped
from nav_msgs.msg import Odometry
import serial
from cobs import cobs
import struct
import cbor2
import crc
import math
import tf2_ros

MAX_SIZE = 512  # 最大受信可能サイズ

class SerialSenderReceiver(Node):

    def __init__(self):
        super().__init__('serial_sender_receiver')

        # パラメータの宣言
        self.declare_parameter('serial_port', '/dev/esp32_usb_serial')
        self.declare_parameter('wheel_radius', 0.0473)  # 車輪の半径 (m)
        self.declare_parameter('wheel_separation', 0.1796)  # 車輪間の距離 (m)
        self.declare_parameter('max_rpm', 200)  # モータの最大回転数

        # パラメータの取得
        serial_port = self.get_parameter('serial_port').get_parameter_value().string_value
        wheel_radius = self.get_parameter('wheel_radius').get_parameter_value().double_value
        wheel_separation = self.get_parameter('wheel_separation').get_parameter_value().double_value
        max_rpm = self.get_parameter('max_rpm').get_parameter_value().integer_value

        # シリアルポートの設定
        self.ser = serial.Serial(serial_port, 115200, timeout=1)  # 送受信用シリアルポート

        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        self.odom_publisher = self.create_publisher(Odometry, 'odom', 10)  # Odometryのパブリッシャー
        self.timer = self.create_timer(0.1, self.read_serial_data)  # タイマー設定

        # インスタンス変数として保持
        self.wheel_radius = wheel_radius
        self.wheel_separation = wheel_separation
        self.max_rpm = max_rpm
        self.buffer = bytearray()

        # ロボットの状態
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0

        # 前回の時間
        self.last_time = self.get_clock().now()

        # 前回のエンコーダー角度（16bit値）
        self.prev_angle_l = None
        self.prev_angle_r = None
        
        # 累積角度（ラジアン）
        self.total_angle_l = 0.0
        self.total_angle_r = 0.0

        # 累積回転数を追加
        self.rotation_count_l = 0
        self.rotation_count_r = 0
        
        # 前回の角度（度）
        self.prev_angle_l_deg = None
        self.prev_angle_r_deg = None

        # オフセット角度を追加（起動時の角度を0にするため）
        self.offset_angle_l_deg = None
        self.offset_angle_r_deg = None

        # TransformBroadcasterのインスタンスを作成
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # 1回転あたりのカウント数を修正
        self.counts_per_revolution = 32767

        # 移動平均フィルタ用変数
        self.filter_window_size = 5  # 移動平均のウィンドウサイズ
        self.angle_history_l = []    # 左輪の角度履歴
        self.angle_history_r = []    # 右輪の角度履歴
        
        # ノイズフィルタ用変数
        self.noise_threshold = 100    # ノイズとみなす変化量の閾値（カウント）
        self.prev_filtered_l = None  # 前回のフィルタリング済み左輪角度
        self.prev_filtered_r = None  # 前回のフィルタリング済み右輪角度

        # CRC16計算機を初期化（CRC16-CCITT）
        self.crc_calculator = crc.Calculator(crc.Configuration(
            width=16,
            polynomial=0x1021,
            init_value=0xFFFF,
            final_xor_value=0x0000,
            reverse_input=False,
            reverse_output=False
        ))

    def cmd_vel_callback(self, msg):
        linear_velocity = msg.linear.x
        angular_velocity = msg.angular.z

        # 左右の車輪の回転速度を計算
        v_r = linear_velocity - (angular_velocity * self.wheel_separation / 2)
        v_l = linear_velocity + (angular_velocity * self.wheel_separation / 2)

        # 回転速度をRPMに変換
        rpm_r = int((v_r / (2 * 3.1416 * self.wheel_radius)) * 60)
        rpm_l = int((v_l / (2 * 3.1416 * self.wheel_radius)) * 60)

        # RPMを最大値に制限
        rpm_r = max(min(rpm_r, self.max_rpm), -self.max_rpm)
        rpm_l = max(min(rpm_l, self.max_rpm), -self.max_rpm)

        # CBORでデータをエンコード
        data_dict = {
            'rpm_l': rpm_l,
            'rpm_r': rpm_r
        }
        cbor_data = cbor2.dumps(data_dict)

        # CRC16を計算
        crc_value = self.calculate_crc16(cbor_data)

        # CRCを含むパケットを作成（データ + CRC16）
        packet_with_crc = cbor_data + crc_value.to_bytes(2, byteorder='big')

        # COBSエンコード
        encoded_data = cobs.encode(packet_with_crc)

        # 終端バイトを追加
        encoded_data += b'\x00'

        # シリアルポートに送信
        self.ser.write(encoded_data)
        #self.get_logger().info(f'Sent RPM values: left={rpm_l}, right={rpm_r}')

    def read_serial_data(self):
        while self.ser.in_waiting > 0:
            data = self.ser.read(1)
            if data == b'\x00':  # 終端バイトに達した場合
                self.process_packet(self.buffer)
                self.buffer.clear()
            else:
                self.buffer.append(data[0])
                if len(self.buffer) > MAX_SIZE:
                    self.get_logger().error('Buffer overflow')
                    self.buffer.clear()

    def process_packet(self, data):
        try:
            decoded_data = cobs.decode(data)
            if len(decoded_data) >= 3:  # 最小サイズ：CBORデータ(1バイト以上) + CRC16(2バイト)
                # CRC16は最後の2バイト（big endian）
                received_crc = int.from_bytes(decoded_data[-2:], byteorder='big')
                cbor_data = decoded_data[:-2]
                calculated_crc = self.calculate_crc16(cbor_data)
                
                if received_crc == calculated_crc:
                    # CBORデータをデコード
                    try:
                        decoded_cbor = cbor2.loads(cbor_data)
                        
                        # 角度情報を取得
                        if isinstance(decoded_cbor, dict):
                            # 新しいCBORフォーマット（辞書型）
                            if 'angle_l' in decoded_cbor and 'angle_r' in decoded_cbor:
                                angle_l = decoded_cbor['angle_l']
                                angle_r = decoded_cbor['angle_r']
                            elif 'L' in decoded_cbor and 'R' in decoded_cbor:
                                angle_l = decoded_cbor['L']
                                angle_r = decoded_cbor['R']
                            else:
                                self.get_logger().warning(f'Unknown CBOR format: {decoded_cbor}')
                                return
                        else:
                            # レガシーサポート：リスト形式の場合
                            if isinstance(decoded_cbor, list) and len(decoded_cbor) >= 2:
                                angle_l, angle_r = decoded_cbor[0], decoded_cbor[1]
                            else:
                                self.get_logger().warning(f'Unsupported CBOR data type: {type(decoded_cbor)}')
                                return
                        
                        # 移動平均フィルタを適用
                        filtered_angle_l = self.apply_moving_average_filter(angle_l, self.angle_history_l)
                        filtered_angle_r = self.apply_moving_average_filter(angle_r, self.angle_history_r)
                        
                        # ノイズ閾値フィルタを適用
                        final_angle_l = self.apply_noise_threshold_filter(filtered_angle_l, 'left')
                        final_angle_r = self.apply_noise_threshold_filter(filtered_angle_r, 'right')
                        
                        # フィルタリング済みの値を度に変換
                        final_angle_l_deg = (final_angle_l / self.counts_per_revolution) * 360.0
                        final_angle_r_deg = (final_angle_r / self.counts_per_revolution) * 360.0
                        
                        self.get_logger().info(f'Raw: L={angle_l}, R={angle_r} | Final counts: L={final_angle_l:.1f}, R={final_angle_r:.1f} | Degrees: L={final_angle_l_deg:.1f}°, R={final_angle_r_deg:.1f}°')
                        
                        # フィルタリング済みの角度でオドメトリを計算
                        self.publish_odometry_from_angles(int(final_angle_l), int(final_angle_r))
                        
                    except cbor2.CBORDecodeError as e:
                        self.get_logger().error(f'CBOR decode error: {e}')
                else:
                    self.get_logger().error(f'CRC16 mismatch: received=0x{received_crc:04X}, calculated=0x{calculated_crc:04X}')
            else:
                self.get_logger().error(f'Received data too short: {len(decoded_data)} bytes')
        except cobs.DecodeError as e:
            self.get_logger().error(f'COBS decode error: {e}')
            

    def publish_odometry_from_angles(self, angle_l, angle_r):
        """エンコーダーの角度情報からオドメトリを計算"""
        current_time = self.get_clock().now()
        
        # 初回はオフセットを設定し、前回値を設定するだけ
        if self.prev_angle_l is None or self.prev_angle_r is None:
            self.prev_angle_l = angle_l
            self.prev_angle_r = angle_r
            self.last_time = current_time
            # 累積距離を0で初期化
            self.total_distance_l = 0.0
            self.total_distance_r = 0.0
            self.get_logger().info('Initialized encoder angles')
            return
        
        # 経過時間を計算
        dt = (current_time - self.last_time).nanoseconds / 1e9
        if dt <= 0:
            return
        
        # 角度差を計算（オーバーフロー考慮）
        angle_diff_l = self.calculate_angle_difference(angle_l, self.prev_angle_l)
        angle_diff_r = self.calculate_angle_difference(angle_r, self.prev_angle_r)
        
        # 角度差をラジアンに変換
        angle_diff_l_rad = (angle_diff_l / self.counts_per_revolution) * 2 * math.pi
        angle_diff_r_rad = (angle_diff_r / self.counts_per_revolution) * 2 * math.pi
        
        # 今回の移動距離（差分）を計算
        distance_diff_l = -angle_diff_l_rad * self.wheel_radius  # 左輪は逆向き
        distance_diff_r = angle_diff_r_rad * self.wheel_radius
    
        # 累積距離を更新
        self.total_distance_l += distance_diff_l
        self.total_distance_r += distance_diff_r
    
        # ロボットの移動距離と回転角を計算（差分を使用）
        distance_center = (distance_diff_l + distance_diff_r) / 2.0
        delta_theta = (distance_diff_r - distance_diff_l) / self.wheel_separation
    
        # ロボットの位置を更新（差分を使用）
        self.x += distance_center * math.cos(self.theta + delta_theta / 2.0)
        self.y += distance_center * math.sin(self.theta + delta_theta / 2.0)
        self.theta += delta_theta
    
        # 角度を-π～πの範囲に正規化
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
    
        # 速度を計算
        linear_velocity = distance_center / dt
        angular_velocity = delta_theta / dt
    
        # 異常値チェック
        if abs(linear_velocity) > 2.0 or abs(angular_velocity) > 5.0:
            #self.get_logger().warn(f'Unusual velocity detected: linear={linear_velocity:.3f}, angular={angular_velocity:.3f}')
            # 異常値の場合は前回値を保持
            self.prev_angle_l = angle_l
            self.prev_angle_r = angle_r
            self.last_time = current_time
            return
    
        # Odometryメッセージを作成
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_footprint'
        
        # ポジションの設定
        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0
        
        # クォータニオンに変換
        odom_quat = self.yaw_to_quaternion(self.theta)
        odom_msg.pose.pose.orientation = odom_quat
        
        # 共分散行列を設定（6x6=36要素、不確実性を表現）
        odom_msg.pose.covariance = [
            0.1,    0.0,    0.0,    0.0,    0.0,    0.0,
            0.0,    0.1,    0.0,    0.0,    0.0,    0.0,
            0.0,    0.0,    999999.0, 0.0,  0.0,    0.0,
            0.0,    0.0,    0.0,    999999.0, 0.0,  0.0,
            0.0,    0.0,    0.0,    0.0,    999999.0, 0.0,
            0.0,    0.0,    0.0,    0.0,    0.0,    0.1
        ]
        
        # ツイストの設定
        odom_msg.twist.twist.linear.x = linear_velocity
        odom_msg.twist.twist.linear.y = 0.0
        odom_msg.twist.twist.angular.z = angular_velocity
        
        # ツイスト共分散行列を設定（6x6=36要素）
        odom_msg.twist.covariance = [
            0.1,    0.0,    0.0,    0.0,    0.0,    0.0,
            0.0,    999999.0, 0.0,  0.0,    0.0,    0.0,
            0.0,    0.0,    999999.0, 0.0,  0.0,    0.0,
            0.0,    0.0,    0.0,    999999.0, 0.0,  0.0,
            0.0,    0.0,    0.0,    0.0,    999999.0, 0.0,
            0.0,    0.0,    0.0,    0.0,    0.0,    0.1
        ]
        
        # Odometryをパブリッシュ
        self.odom_publisher.publish(odom_msg)
        
        # TF変換を作成してパブリッシュ
        transform = TransformStamped()
        transform.header.stamp = current_time.to_msg()
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'base_footprint'
        
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.translation.z = 0.0
        transform.transform.rotation = odom_quat
        
        # tfをブロードキャスト
        self.tf_broadcaster.sendTransform(transform)
        
        # 前回の値を更新
        self.prev_angle_l = angle_l
        self.prev_angle_r = angle_r
        self.last_time = current_time
        
        # デバッグ情報（必要に応じて）
        if self.get_logger().get_effective_level() <= 10:  # DEBUG level
            self.get_logger().debug(f'Odom: x={self.x:.3f}, y={self.y:.3f}, theta={self.theta:.3f}, v={linear_velocity:.3f}, w={angular_velocity:.3f}')
        
        # 通常のログ（INFO）でも度で表示
        theta_deg = math.degrees(self.theta)
        #self.get_logger().info(f'Published odometry: x={self.x:.3f}, y={self.y:.3f}, theta={theta_deg:.1f}°')

    def detect_rotation_change(self, current_angle_deg, prev_angle_deg):
        """回転数の変化を検出する関数"""
        rotation_change = 0
        
        # 360度から0度への変化（正方向の回転）
        if prev_angle_deg > 270 and current_angle_deg < 90:
            rotation_change = 1
            self.get_logger().info('Detected positive rotation: 360° -> 0°')
        
        # 0度から360度への変化（負方向の回転）
        elif prev_angle_deg < 90 and current_angle_deg > 270:
            rotation_change = -1
            self.get_logger().info('Detected negative rotation: 0° -> 360°')
        
        return rotation_change
    
    def calculate_angle_difference(self, current_angle, prev_angle):
        """16bitエンコーダーのオーバーフローを考慮した角度差計算"""
        diff = current_angle - prev_angle
        
        # 0～32767の範囲でオーバーフロー処理
        # 半回転（16384）以上の差は逆方向の回転と判断
        if diff > self.counts_per_revolution / 2:
            diff -= self.counts_per_revolution
        elif diff < -self.counts_per_revolution / 2:
            diff += self.counts_per_revolution

        return diff

    def apply_moving_average_filter(self, new_value, history):
        """移動平均フィルタを適用"""
        # 新しい値を履歴に追加
        history.append(new_value)
        
        # ウィンドウサイズを超えた場合、古い値を削除
        if len(history) > self.filter_window_size:
            history.pop(0)
        
        # 移動平均を計算
        return sum(history) / len(history)

    def apply_noise_threshold_filter(self, new_value, wheel_side):
        """ノイズ閾値フィルタを適用（急激な変化を抑制）"""
        if wheel_side == 'left':
            prev_value = self.prev_filtered_l
        else:  # 'right'
            prev_value = self.prev_filtered_r
        
        # 初回の場合はそのまま返す
        if prev_value is None:
            if wheel_side == 'left':
                self.prev_filtered_l = new_value
            else:
                self.prev_filtered_r = new_value
            return new_value
        
        # 変化量を計算（16bitオーバーフロー考慮）
        change = self.calculate_change_with_overflow(new_value, prev_value)
        
        # 閾値を超える変化の場合は制限
        if abs(change) > self.noise_threshold:
            # 変化量を閾値に制限
            limited_change = self.noise_threshold if change > 0 else -self.noise_threshold
            filtered_value = prev_value + limited_change
            
            # 16bit範囲に正規化
            filtered_value = self.normalize_16bit_value(filtered_value)
            
            #self.get_logger().warn(f'{wheel_side} wheel: Large change detected ({change:.1f}), limited to {limited_change}')
        else:
            filtered_value = new_value
        
        # 前回値を更新
        if wheel_side == 'left':
            self.prev_filtered_l = filtered_value
        else:
            self.prev_filtered_r = filtered_value
        
        return filtered_value

    def calculate_change_with_overflow(self, current_value, prev_value):
        """16bitオーバーフローを考慮した変化量計算"""
        change = current_value - prev_value
        
        # 0～65535の範囲でオーバーフロー処理
        # 半回転（32768）以上の差は逆方向の回転と判断
        if change > 32768:
            change -= 65536
        elif change < -32768:
            change += 65536
            
        return change

    def normalize_16bit_value(self, value):
        """値を16bit範囲（0～65535）に正規化"""
        while value < 0:
            value += 65536
        while value >= 65536:
            value -= 65536
        return value

    def publish_odometry(self, rpm_l, rpm_r):
        # 現在の時間を取得
        current_time = self.get_clock().now()

        # RPMをm/sに変換
        v_l = (rpm_l / 60.0) * (2 * math.pi * self.wheel_radius)
        v_r = (rpm_r / 60.0) * (2 * math.pi * self.wheel_radius)

        # ロボットの速度を計算
        linear_velocity = (v_r + v_l) / 2
        angular_velocity = (v_r - v_l) / self.wheel_separation

        # 経過時間を計算
        dt = (current_time - self.last_time).nanoseconds / 1e9

        # ロボットの位置を更新
        self.x += linear_velocity * math.cos(self.theta) * dt
        self.y += linear_velocity * math.sin(self.theta) * dt
        self.theta += angular_velocity * dt

        # Odometryメッセージを作成
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_footprint'  # 修正箇所

        # ポジションの設定
        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0

        # クォータニオンに変換
        odom_quat = self.yaw_to_quaternion(self.theta)
        odom_msg.pose.pose.orientation = odom_quat

        # ツイストの設定
        odom_msg.twist.twist.linear.x = linear_velocity
        odom_msg.twist.twist.linear.y = 0.0
        odom_msg.twist.twist.angular.z = angular_velocity

        # Odometryをパブリッシュ
        self.odom_publisher.publish(odom_msg)

        # TF変換を作成してパブリッシュ
        transform = TransformStamped()
        transform.header.stamp = current_time.to_msg()
        transform.header.frame_id = 'odom'
        transform.child_frame_id = 'base_footprint'
        
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.translation.z = 0.0
        transform.transform.rotation = odom_quat

        # tfをブロードキャスト
        self.tf_broadcaster.sendTransform(transform)

        # 前回の時間を更新
        self.last_time = current_time

    def yaw_to_quaternion(self, yaw):
        """ ヨー角からクォータニオンを生成 """
        half_yaw = yaw / 2.0
        q = Quaternion()
        q.z = math.sin(half_yaw)
        q.w = math.cos(half_yaw)
        return q

    def calculate_crc16(self, data):
        """CRC16を計算（CRC16-CCITT）"""
        return self.crc_calculator.checksum(data)

def main(args=None):
    rclpy.init(args=args)
    serial_sender_receiver = SerialSenderReceiver()
    rclpy.spin(serial_sender_receiver)
    serial_sender_receiver.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
