import os
import subprocess
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
    SetLaunchConfiguration,
)
from launch.actions.reset_launch_configurations import ResetLaunchConfigurations
from launch.event_handlers import OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _check_no_running_gazebo(context, *args, **kwargs):
    # Inspect conflicts without signalling any process, including stale ones.
    try:
        running = []
        for name in ("gzserver", "gzclient"):
            result = subprocess.run(
                ["pgrep", "-x", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            if result.returncode not in (0, 1):
                raise RuntimeError(f"[gazebo_bringup] Could not inspect {name}.")
            running.append(result.returncode == 0)
        listeners = subprocess.run(
            ["ss", "-H", "-lnt", "sport = :11345"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(
            "[gazebo_bringup] Could not check for an existing Gazebo; "
            "no processes were stopped."
        ) from error

    # 既存Gazeboやマスター用ポート占有がある場合は即中断する。
    if any(running) or listeners.stdout.strip():
        raise RuntimeError(
            "[gazebo_bringup] 既存Gazeboまたは11345ポート占有を検出。"
            "起動元の端末で終了してから再実行してください。"
            "このlaunchから既存プロセスを終了することはありません。"
        )

    messages = []
    if LaunchConfiguration("cleanup_stale_gazebo").perform(context).lower() in (
        "1", "true", "yes", "on"
    ):
        messages.append(LogInfo(
            msg="[gazebo_bringup] cleanup_stale_gazebo is ignored; "
                "existing processes are never terminated."
        ))
    return messages + [LogInfo(msg="[gazebo_bringup] No existing Gazebo process detected.")]


def _make_world_with_state(context, temporary_files, *args, **kwargs):
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
    temporary_files.append(path)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(world_xml)

    return [
        LogInfo(msg=f"[gazebo_bringup] generated temp world: {path}"),
        SetLaunchConfiguration("world_path", path),
    ]


def _create_urdf_and_rsp(context, temporary_files, *args, **kwargs):
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

    # Generate once before starting consumers; no writer can outlive cleanup.
    robot_description = Command(
        [FindExecutable(name="xacro"), " ", xacro_file]
    ).perform(context)
    fd, urdf_path = tempfile.mkstemp(prefix="robot_", suffix=".urdf")
    temporary_files.append(urdf_path)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(robot_description)

    # gazebo_ros2_control からも安定して参照できるように robot_description を明示。
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="megarover3_robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": ParameterValue(
                    robot_description,
                    value_type=str,
                ),
                "use_sim_time": True,
            }
        ],
    )

    return [
        SetLaunchConfiguration("urdf_path", urdf_path),
        LogInfo(msg=f"[gazebo_bringup] generated temp urdf: {urdf_path}"),
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


def _cleanup_temp_files(context, temporary_files, *args, **kwargs):
    # Paths belong to this launch instance, never to caller-supplied arguments.
    pending = []
    messages = []
    for path in temporary_files:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as error:
            pending.append(path)
            messages.append(LogInfo(
                msg=f"[gazebo_bringup] Could not remove temporary file {path}: {error}"
            ))
    temporary_files[:] = pending
    return messages + [LogInfo(msg="[gazebo_bringup] Temporary-file cleanup completed.")]


def generate_launch_description():
    temporary_files = []
    rover = LaunchConfiguration("rover")
    gui = LaunchConfiguration("gui")
    verbose = LaunchConfiguration("verbose")
    world_path = LaunchConfiguration("world_path")
    urdf_path = LaunchConfiguration("urdf_path")
    spawn_z = LaunchConfiguration("spawn_z")

    check_no_running_gazebo = OpaqueFunction(function=_check_no_running_gazebo)
    make_world = OpaqueFunction(
        function=_make_world_with_state, kwargs={"temporary_files": temporary_files}
    )
    create_urdf_and_rsp = OpaqueFunction(
        function=_create_urdf_and_rsp, kwargs={"temporary_files": temporary_files}
    )
    resolve_spawn_z = OpaqueFunction(function=_resolve_spawn_z)

    # Include server/client actions so this launch owns their shutdown.
    # Isolate Gazebo arguments while preserving the caller's environment.
    gazebo = GroupAction(
        scoped=True,
        actions=[
            ResetLaunchConfigurations({"gui": gui, "verbose": verbose, "world": world_path}),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory("gazebo_ros"), "launch", "gazebo.launch.py"
            ))),
        ],
    )

    spawn = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=[
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
            "if ros2 control list_controllers 2>/dev/null | grep -Eq '^joint_state_broadcaster[[:space:]].*[[:space:]]active'; then "
            "echo '[gazebo_bringup] joint_state_broadcaster already active'; "
            "else "
            "ros2 run controller_manager spawner joint_state_broadcaster "
            "--controller-manager-timeout 120 "
            "--service-call-timeout 120 || exit 1; "
            "fi; "
            "if ros2 control list_controllers 2>/dev/null | grep -Eq '^wheel_velocity_controller[[:space:]].*[[:space:]]active'; then "
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
        OnShutdown(on_shutdown=[OpaqueFunction(
            function=_cleanup_temp_files, kwargs={"temporary_files": temporary_files}
        )])
    )

    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("verbose", default_value="false"),
        DeclareLaunchArgument("rover", default_value="mega3"),
        DeclareLaunchArgument(
            "cleanup_stale_gazebo", default_value="false",
            description="Deprecated compatibility argument; never stops existing processes.",
        ),
        DeclareLaunchArgument("physics", default_value="ode"),
        DeclareLaunchArgument("spawn_z", default_value=""),
        DeclareLaunchArgument("max_step_size", default_value="0.002"),
        DeclareLaunchArgument("real_time_update_rate", default_value="500"),
        DeclareLaunchArgument("state_update_rate", default_value="15"),

        on_shutdown_cleanup,
        check_no_running_gazebo,
        make_world,
        create_urdf_and_rsp,
        resolve_spawn_z,
        gazebo,
        spawn,
        spawners_group,
        rover_twist_relay,
        gazebo_odom_bridge,
    ])
