# メガローバー ROS 2 Jazzyパッケージ

<p align="center">
  <img src="./images/mega3.png" width="600" />
</p>

メガローバーVer.3.0とメガローバーF120AをROS 2で利用するためのパッケージです。
実機との通信、オドメトリーの出力、RVizでのモデル表示、
SLAMによる地図作成、Nav2によるナビゲーションに対応します。
製品の接続・設定・ファームウェアの書き込みは、ご購入時に提供する取扱説明書を参照してください。

## 対応環境

| 項目 | 対応内容 |
| --- | --- |
| OS / ROS | Ubuntu 24.04 / ROS 2 Jazzy |
| ロボット | メガローバーVer.3.0（`mega3`）、メガローバーF120A（`f120a`） |
| ファームウェア | 両機種とも30.11.0以上 |
| 通信 | micro-ROS Agent経由のUSBシリアル or Wi-Fi接続 |

## 環境セットアップ

PCの環境構築、ROS 2・依存パッケージの導入、本パッケージの取得・ビルドについては、
製品の取扱説明書を参照してください。
取扱説明書に従ってセットアップを完了してから、以下の使用手順を実行してください。

## 実機の基本起動

取扱説明書に従ってロボットとPCを接続し、各コマンドを別のターミナルで実行します。
シリアルポート名は実際の接続先に合わせてください。

micro-ROS Agentを起動します。

```bash
source ~/microros_ws/install/local_setup.bash
ros2 run micro_ros_agent micro_ros_agent serial \
  --dev /dev/ttyUSB0 --baudrate 921600 -v4
```

モデル表示とオドメトリーの出力を開始します。

```bash
source ~/ros2_ws/install/local_setup.bash
ros2 launch megarover3_bringup robot.launch.py
```

`rover`の既定値は`mega3`です。F120Aを使用する場合は次のように指定します。

```bash
ros2 launch megarover3_bringup robot.launch.py rover:=f120a
```

`robot.launch.py`はRVizとオドメトリー変換ノードを起動します。
通信が成立すると`odom`と`odom → base_footprint`のTFを出力し、
RVizでモデルの位置・向きに反映します。出力は別のターミナルで確認できます。

```bash
source ~/ros2_ws/install/local_setup.bash
ros2 topic echo /odom
```

## SLAM

本パッケージのSLAM機能はSLAM Toolboxを使用します。
`slam.launch.py`は非同期モード、`slam_sync.launch.py`は同期モードを起動します。
LiDARの計測データとオドメトリーから地図を作成します。
以下はLRFオプションTG30を使用する例です。各コマンドは別のターミナルで実行してください。

### TG30とSLAM Toolboxの準備

取扱説明書に従い、YDLidar SDK、LiDARドライバー、SLAM Toolboxのセットアップを完了してください。
TG30を接続し、[TG30.yaml](./megarover3_bringup/params/TG30.yaml)の設定を実機に合わせてください。
LiDAR用ポートの既定値は`/dev/ttyUSB1`です。micro-ROS Agent用のポートと区別してください。

LiDARの取り付け位置・向きは、[モデルのREADME](https://github.com/vstoneofficial/megarover_description/tree/jazzy)を参照して、
使用する機種のTG30オプションを設定してください。`/scan`のframeとモデルのTFを一致させます。

### SLAM Toolboxで地図を作成する

1. 「実機の基本起動」の手順でmicro-ROS Agentを起動し、実機と通信できる状態にします。
   `robot.launch.py`が起動している場合は、その端末でCtrl+Cを押して終了します。

2. モデル表示、オドメトリー出力、LiDARをまとめて起動します。

   ```bash
   source ~/ros2_ws/install/local_setup.bash
   ros2 launch megarover3_bringup nav_robot.launch.py rover:=mega3
   ```

   F120Aでは`rover:=f120a`を指定します。LiDARのポートが異なる場合は、
   同じコマンドに`lidar_port:=/dev/ttyUSB2`などを追加してください。

3. 新しいターミナルでSLAMを起動します。

   ```bash
   source ~/ros2_ws/install/local_setup.bash
   ros2 launch megarover3_navigation slam.launch.py use_sim_time:=false
   ```

   SLAM用のRVizが開き、`/scan`の計測点と`/map`の地図を表示します。
   Fixed Frameは`map`を使用します。

4. 付属のVS-C3無線コントローラ、またはROS 2のteleopでロボットを動かし、地図を作成します。
   キーボードで操作する場合は、さらに別のターミナルで次を実行します。

   ```bash
   source ~/ros2_ws/install/local_setup.bash
   ros2 run teleop_twist_keyboard teleop_twist_keyboard \
     --ros-args -r cmd_vel:=rover_twist -p stamped:=false
   ```

   操作キーは端末に表示される案内を参照してください。
   RVizで周囲の形状が地図に反映されることを確認しながら走行します。

SLAMの設定は[mapper_params_online_async.yaml](./megarover3_navigation/config/mapper_params_online_async.yaml)にあります。
設定を別ファイルで管理する場合は、SLAMの起動コマンドに
`slam_params_file:=/absolute/path/to/slam_params.yaml`を追加します。

### 作成した地図を保存する

SLAMが起動している間に、別のターミナルで地図を保存します。
次の例では、本パッケージの`maps`フォルダーに`my_map`という名前で保存します。

```bash
source ~/ros2_ws/install/local_setup.bash
ros2 run nav2_map_server map_saver_cli \
  -f ~/ros2_ws/src/megarover3_ros2/megarover3_navigation/maps/my_map
```

保存に成功すると、`my_map.yaml`と`my_map.pgm`が作成されます。
地図を移動・コピーする場合は、この2ファイルを同じフォルダーに置いてください。

保存後にNav2へ切り替える場合は、ロボットを停止させ、
SLAMとteleopの端末をCtrl+Cで終了します。
micro-ROS Agentと`nav_robot.launch.py`は、そのまま利用できます。

## Nav2を使用したナビゲーション

保存した地図を使い、ロボットの現在位置を推定しながら目標位置まで移動します。
SLAMで作成した地図のYAMLファイルと画像ファイルを用意してください。
Nav2に必要な依存パッケージの導入については、製品の取扱説明書を参照してください。

### 実機とLiDARを起動する

micro-ROS Agentを起動したうえで、実機・LiDAR用のlaunchを実行します。
SLAMの手順から継続している場合は、起動済みのものを使用してください。

```bash
source ~/ros2_ws/install/local_setup.bash
ros2 launch megarover3_bringup nav_robot.launch.py rover:=mega3
```

F120Aでは`rover:=f120a`を指定します。基本起動の`robot.launch.py`と重複して起動しないでください。

### 保存した地図でNav2を起動する

新しいターミナルで、地図YAMLのフルパスを`map:=`に指定します。
以下は、前の手順で保存した`my_map.yaml`を使用する例です。

```bash
source ~/ros2_ws/install/local_setup.bash
ros2 launch megarover3_navigation navigation.launch.py \
  rover:=mega3 \
  map:=$HOME/ros2_ws/src/megarover3_ros2/megarover3_navigation/maps/my_map.yaml \
  use_sim_time:=false
```

F120Aでは、このコマンドも`rover:=f120a`に変更します。
地図は必ず使用する環境のものを指定してください。`map`を省略すると付属のサンプル地図を使用します。

### RVizで初期位置と目標位置を指定する

1. Nav2用のRVizで地図が表示され、Fixed Frameが`map`であることを確認します。
2. ツールバーの「2D Pose Estimate」を選択し、地図上でロボットの現在位置から向きの方向へドラッグします。
   LiDARの計測点が地図の壁などに重なることを確認してください。
3. 「Navigation 2」パネルでNav2の起動状態を確認し、
   ツールバーの「Nav2 Goal」で目標位置と到着時の向きをドラッグして指定します。
4. ロボットが経路に沿って移動し、目標位置に到着することを確認します。
   移動を取り消す場合は「Navigation 2」パネルの「Cancel」を使用します。

Nav2を使用するときは、キーボード・マウス操作など、
`rover_twist`へ別の速度指令を送信するノードを終了しておいてください。
SLAMによる地図作成から切り替える場合は、SLAMも終了しておきます。

### 設定を調整する

Nav2の設定は機種に応じて自動選択されます。

| 機種 | 設定ファイル |
| --- | --- |
| メガローバーVer.3.0 | [mega3_nav2_params.yaml](./megarover3_navigation/config/mega3_nav2_params.yaml) |
| メガローバーF120A | [f120a_nav2_params.yaml](./megarover3_navigation/config/f120a_nav2_params.yaml) |

ロボットの搭載物や使用環境に合わせて、footprint、速度・加速度、障害物検出などの設定を調整してください。
別の設定ファイルを使用する場合は、Nav2の起動コマンドに
`params_file:=/absolute/path/to/nav2_params.yaml`を追加します。

## 確認状況

実機で基本launchの起動、通信、オドメトリー出力、モデル表示とオドメトリーの反映、
SLAMによる地図作成およびNav2によるナビゲーションの動作を確認しています。
Gazeboを使用したシミュレーションは対応中です。
現時点の公開版はGazeboの起動機能を提供していません。
RVizによるモデル表示と、実機でのSLAM・Nav2は上記の手順で利用できます。

## パッケージ

| パッケージ | 用途 |
| --- | --- |
| `megarover3_bringup` | 実機の基本起動、オドメトリー変換 |
| `megarover_description` | ロボットモデル |
| `megarover3_navigation` | SLAM・Nav2の設定とlaunch |
| `megarover3` | メタパッケージ |

## ライセンス

[Apache License 2.0](./LICENSE)
