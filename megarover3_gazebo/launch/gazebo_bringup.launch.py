import os
import subprocess
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
    SetLaunchConfiguration,
)
from launch.event_handlers import OnShutdown
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node


def _check_no_running_gazebo(context, *args, **kwargs):
    has_gzserver = subprocess.run(
        ["pgrep", "gzserver"], stdout=subprocess.DEVNULL
    ).returncode == 0
    has_gzclient = subprocess.run(
        ["pgrep", "gzclient"], stdout=subprocess.DEVNULL
    ).returncode == 0
    port_in_use = subprocess.run(
        ["bash", "-lc", "ss -lnt | grep -q ':11345'"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0

    # 既存Gazeboやマスター用ポート占有がある場合は即中断する。
    if has_gzserver or has_gzclient or port_in_use:
        raise RuntimeError(
            "[gazebo_bringup] 既存Gazeboまたは11345ポート占有を検出。"
            "重複起動を解消してから再実行してください。"
        )

    return [LogInfo(msg="[gazebo_bringup] No existing Gazebo process detected.")]


def _make_world_with_state(context, *args, **kwargs):
    physics_type = LaunchConfiguration("physics").perform(context)
    if physics_type not in ("ode", "bullet"):
        physics_type = "ode"

    max_step_size = LaunchConfiguration("max_step_size").perform(context)
    real_time_update_rate = LaunchConfiguration("real_time_update_rate").perform(context)
    state_update_rate = LaunchConfiguration("state_update_rate").perform(context)

    try:
        max_step_size_val = float(max_step_size)
    except ValueError:
        max_step_size_val = 0.002
    try:
        real_time_update_rate_val = float(real_time_update_rate)
    except ValueError:
        real_time_update_rate_val = 500.0
    try:
        state_update_rate_val = float(state_update_rate)
    except ValueError:
        state_update_rate_val = 15.0

    world_xml = f"""<?xml version="1.0"?>
<sdf version="1.6">
  <world name="default">
    <physics type="{physics_type}">
      <max_step_size>{max_step_size_val}</max_step_size>
      <real_time_update_rate>{real_time_update_rate_val}</real_time_update_rate>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <gravity>0 0 -9.81</gravity>
    <include><uri>model://ground_plane</uri></include>
    <include><uri>model://sun</uri></include>
    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">
      <ros><namespace>/</namespace></ros>
      <publish_model_state>true</publish_model_state>
      <publish_link_state>true</publish_link_state>
      <update_rate>{state_update_rate_val}</update_rate>
      <model_states_topic>/model_states</model_states_topic>
      <link_states_topic>/link_states</link_states_topic>
    </plugin>
  </world>
</sdf>
"""

    fd, path = tempfile.mkstemp(prefix="megarover3_world_", suffix=".world")
    with os.fdopen(fd, "w") as f:
        f.write(world_xml)

    return [
        LogInfo(msg=f"[gazebo_bringup] generated temp world: {path}"),
        SetLaunchConfiguration("world_path", path),
    ]


def _create_urdf_and_rsp(context, *args, **kwargs):
    rover = LaunchConfiguration("rover").perform(context)

    urdf_dir = os.path.join(
        get_package_share_directory("megarover_description"),
        "urdf",
    )

    xacro_map = {
        "mega3": "mega3.xacro",
        "f120a": "f120a.xacro",
        "s40a_lb": "s40a_lb.xacro",
    }
    if rover not in xacro_map:
        raise RuntimeError(f"[gazebo_bringup] Unknown rover type: {rover}")

    xacro_file = os.path.join(urdf_dir, xacro_map[rover])

    fd, urdf_path = tempfile.mkstemp(prefix="robot_", suffix=".urdf")
    os.close(fd)

    gen = ExecuteProcess(
        cmd=[FindExecutable(name="xacro"), xacro_file, "-o", urdf_path],
        output="screen",
    )

    # gazebo_ros2_control からも安定して参照できるように robot_description を明示。
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": Command(
                    [FindExecutable(name="xacro"), " ", xacro_file]
                ),
                "use_sim_time": True,
            }
        ],
    )

    return [
        SetLaunchConfiguration("urdf_path", urdf_path),
        LogInfo(msg=f"[gazebo_bringup] generated temp urdf: {urdf_path}"),
        gen,
        rsp,
    ]


def _resolve_spawn_z(context, *args, **kwargs):
    rover = LaunchConfiguration("rover").perform(context)
    spawn_z_arg = LaunchConfiguration("spawn_z").perform(context).strip()

    if spawn_z_arg:
        spawn_z = spawn_z_arg
    else:
        default_z = {
            "mega3": "0.03",
            "f120a": "0.03",
            "s40a_lb": "0.03",
        }
        spawn_z = default_z.get(rover, "0.03")

    return [
        SetLaunchConfiguration("spawn_z", spawn_z),
        LogInfo(msg=f"[gazebo_bringup] spawn z for {rover}: {spawn_z}"),
    ]


def _cleanup_temp_files(context, *args, **kwargs):
    world_path = LaunchConfiguration("world_path").perform(context)
    urdf_path = LaunchConfiguration("urdf_path").perform(context)

    for p in (world_path, urdf_path):
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    return [LogInfo(msg="[gazebo_bringup] Cleaned up temp files")]


def generate_launch_description():
    rover = LaunchConfiguration("rover")
    gui = LaunchConfiguration("gui")
    verbose = LaunchConfiguration("verbose")
    world_path = LaunchConfiguration("world_path")
    urdf_path = LaunchConfiguration("urdf_path")
    spawn_z = LaunchConfiguration("spawn_z")

    check_no_running_gazebo = OpaqueFunction(function=_check_no_running_gazebo)
    make_world = OpaqueFunction(function=_make_world_with_state)
    create_urdf_and_rsp = OpaqueFunction(function=_create_urdf_and_rsp)
    resolve_spawn_z = OpaqueFunction(function=_resolve_spawn_z)

    gazebo = ExecuteProcess(
        cmd=[
            "ros2",
            "launch",
            "gazebo_ros",
            "gazebo.launch.py",
            ["gui:=", gui],
            ["verbose:=", verbose],
            ["world:=", world_path],
        ],
        output="screen",
    )

    spawn = ExecuteProcess(
        cmd=[
            "ros2",
            "run",
            "gazebo_ros",
            "spawn_entity.py",
            "-entity",
            rover,
            "-file",
            urdf_path,
            "-z",
            spawn_z,
        ],
        output="screen",
    )

    # 既にactiveなcontrollerは再設定せず、未起動なものだけ順次有効化する。
    spawners_group = ExecuteProcess(
        cmd=[
            "bash",
            "-lc",
            "sleep 12.0; "
            "until ros2 control list_controllers >/dev/null 2>&1; do "
            "echo '[gazebo_bringup] waiting for /controller_manager/list_controllers'; "
            "sleep 1.0; "
            "done; "
            "if ros2 control list_controllers 2>/dev/null | grep -Eq 'joint_state_broadcaster\\s+active'; then "
            "echo '[gazebo_bringup] joint_state_broadcaster already active'; "
            "else "
            "ros2 run controller_manager spawner joint_state_broadcaster "
            "--controller-manager-timeout 120 "
            "--service-call-timeout 120 || exit 1; "
            "fi; "
            "if ros2 control list_controllers 2>/dev/null | grep -Eq 'wheel_velocity_controller\\s+active'; then "
            "echo '[gazebo_bringup] wheel_velocity_controller already active'; "
            "else "
            "ros2 run controller_manager spawner wheel_velocity_controller "
            "--controller-manager-timeout 120 "
            "--service-call-timeout 120 || exit 1; "
            "fi",
        ],
        output="screen",
    )

    rover_twist_relay = Node(
        package="megarover_description",
        executable="rover_twist_relay.py",
        name="rover_twist_relay",
        output="screen",
        parameters=[
            os.path.join(
                get_package_share_directory("megarover_description"),
                "params",
                "rover_twist_relay.yaml",
            ),
            {
                "rover": rover,
                "use_sim_time": True,
            },
        ],
    )

    gazebo_odom_bridge = Node(
        package="megarover3_bringup",
        executable="gazebo_odom_bridge",
        name="gazebo_odom_bridge",
        output="screen",
        parameters=[
            {"model_name": rover},
            {"base_frame": "base_footprint"},
            {"use_sim_time": True},
        ],
    )

    on_shutdown_cleanup = RegisterEventHandler(
        OnShutdown(on_shutdown=[OpaqueFunction(function=_cleanup_temp_files)])
    )

    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("verbose", default_value="false"),
        DeclareLaunchArgument("rover", default_value="mega3"),
        DeclareLaunchArgument("physics", default_value="ode"),
        DeclareLaunchArgument("spawn_z", default_value=""),
        DeclareLaunchArgument("max_step_size", default_value="0.002"),
        DeclareLaunchArgument("real_time_update_rate", default_value="500"),
        DeclareLaunchArgument("state_update_rate", default_value="15"),

        check_no_running_gazebo,
        make_world,
        create_urdf_and_rsp,
        resolve_spawn_z,
        gazebo,
        spawn,
        spawners_group,
        rover_twist_relay,
        gazebo_odom_bridge,
        on_shutdown_cleanup,
    ])
