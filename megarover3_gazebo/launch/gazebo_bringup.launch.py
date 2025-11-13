#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    RegisterEventHandler,
    LogInfo,
    OpaqueFunction,
    SetLaunchConfiguration
)
from launch.event_handlers import OnProcessStart, OnProcessExit
from launch.substitutions import (
    Command,
    PathJoinSubstitution,
    LaunchConfiguration,
    TextSubstitution,
    FindExecutable
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_prefix


def _make_world_with_state(context, *args, **kwargs):
    world_xml = """<?xml version="1.0"?>
<sdf version="1.6">
  <world name="default">
    <include><uri>model://ground_plane</uri></include>
    <include><uri>model://sun</uri></include>

    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">
      <ros><namespace>/</namespace></ros>
      <publish_model_state>true</publish_model_state>
      <publish_link_state>true</publish_link_state>
      <update_rate>30</update_rate>
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


def generate_launch_description():

    use_sim_time = LaunchConfiguration("use_sim_time")
    gui = LaunchConfiguration("gui")
    verbose = LaunchConfiguration("verbose")
    model_name = LaunchConfiguration("model_name")
    world_path = LaunchConfiguration("world_path")

    # 0: clean lock file
    clean_lock = ExecuteProcess(
        cmd=["rm", "-f", "/tmp/.gazebo/lock"],
        output="screen"
    )

    # 1: kill old Gazebo
    kill_gz = ExecuteProcess(
        cmd=["killall", "-9", "gzserver", "gzclient"],
        output="screen"
    )

    # 2: robot_state_publisher (Node)
    urdf_path = PathJoinSubstitution(
        [FindPackageShare("megarover_description"), "urdf", "mega3.xacro"]
    )
    xacro_cmd = Command(
        [PathJoinSubstitution([FindExecutable(name="xacro")]), " ", urdf_path]
    )
    robot_description = {"robot_description": ParameterValue(xacro_cmd, value_type=str)}

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"use_sim_time": use_sim_time}, robot_description],
        output="log"
    )

    # world generation (not sequenced)
    make_world = OpaqueFunction(function=_make_world_with_state)

    # 3: Gazebo
    gazebo = ExecuteProcess(
        cmd=[
            "ros2", "launch", "gazebo_ros", "gazebo.launch.py",
            ["gui:=", gui],
            ["verbose:=", verbose],
            ["world:=", world_path],
        ],
        output="screen"
    )

    # 4: spawn robot
    spawn = ExecuteProcess(
        cmd=[
            "ros2", "run", "gazebo_ros", "spawn_entity.py",
            "-entity", model_name,
            "-topic", "robot_description"
        ],
        output="screen"
    )

    # 5: joint_state_broadcaster
    jsb = ExecuteProcess(
        cmd=[
            "ros2", "run", "controller_manager", "spawner",
            "joint_state_broadcaster",
            "--controller-manager", "/controller_manager",
            "--controller-manager-timeout", "60"
        ],
        output="screen"
    )

    # 6: diff_drive_controller
    diff = ExecuteProcess(
        cmd=[
            "ros2", "run", "controller_manager", "spawner",
            "diff_drive_controller",
            "--controller-manager", "/controller_manager",
            "--controller-manager-timeout", "60"
        ],
        output="screen"
    )

    # relay (no sequence needed)
    pkg_prefix = get_package_prefix('megarover_description')
    relay_script = os.path.join(pkg_prefix, 'lib', 'megarover_description', 'rover_twist_relay.py')
    relay = ExecuteProcess(
        cmd=["python3", relay_script],
        output="screen"
    )

    # ------ Sequence control (required only where dependency exists) ------
    seq1 = RegisterEventHandler(OnProcessExit(target_action=clean_lock, on_exit=[kill_gz]))
    seq2 = RegisterEventHandler(OnProcessExit(target_action=kill_gz, on_exit=[rsp]))
    seq3 = RegisterEventHandler(OnProcessStart(target_action=rsp, on_start=[gazebo]))
    seq4 = RegisterEventHandler(OnProcessStart(target_action=gazebo, on_start=[spawn]))
    seq5 = RegisterEventHandler(OnProcessStart(target_action=spawn, on_start=[jsb]))
    seq6 = RegisterEventHandler(OnProcessStart(target_action=jsb, on_start=[diff]))

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("verbose", default_value="false"),
        DeclareLaunchArgument("model_name", default_value="megarover3"),

        clean_lock,
        make_world,
        seq1,
        seq2,
        seq3,
        seq4,
        seq5,
        seq6,

        relay
    ])

