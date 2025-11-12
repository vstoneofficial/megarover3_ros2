#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    LogInfo,
    SetLaunchConfiguration,
    RegisterEventHandler,
    ExecuteProcess,   # © ÇÁ
)
from launch.event_handlers import OnProcessStart
from launch.substitutions import (
    Command,
    PathJoinSubstitution,
    LaunchConfiguration,
    TextSubstitution,
    FindExecutable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_prefix   # © ÇÁiinstall/libQÆpj


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
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    gui = LaunchConfiguration("gui", default="true")
    verbose = LaunchConfiguration("verbose", default="false")
    model_name = LaunchConfiguration("model_name", default="megarover3")

    # URDFixacroWJj
    urdf_path = PathJoinSubstitution(
        [FindPackageShare("megarover_description"), "urdf", "mega3.xacro"]
    )
    xacro_cmd = Command(
        [PathJoinSubstitution([FindExecutable(name="xacro")]), TextSubstitution(text=" "), urdf_path]
    )
    robot_description = {"robot_description": ParameterValue(xacro_cmd, value_type=str)}

    # Robot State Publisher
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"use_sim_time": use_sim_time}, robot_description],
        output="log",
    )

    # GazeboN®
    make_world = OpaqueFunction(function=_make_world_with_state)
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([FindPackageShare("gazebo_ros"), "launch", "gazebo.launch.py"])]
        ),
        launch_arguments={
            "gui": gui,
            "verbose": verbose,
            "world": LaunchConfiguration("world_path"),
        }.items(),
    )

    # fSpawn
    spawn = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=["-entity", model_name, "-topic", "robot_description"],
        output="log",
    )

    # Rg[ÌSpawner
    spawner_jsb = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager", "/controller_manager",
            "--controller-manager-timeout", "60",
        ],
        output="log",
    )

    spawner_diff = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "diff_drive_controller",
            "--controller-manager", "/controller_manager",
            "--controller-manager-timeout", "60",
        ],
        output="log",
    )

    # rover_twist_relay.py ð¼ÚN®iinstall/lib/... ð³mÉQÆj
    pkg_prefix = get_package_prefix('megarover_description')
    relay_script = os.path.join(pkg_prefix, 'lib', 'megarover_description', 'rover_twist_relay.py')

    relay_node = ExecuteProcess(
        cmd=['python3', relay_script],
        output='screen'
    )

    # CxgnhiSpawn®¹ãÉRg[N®j
    jsb_on_spawn = RegisterEventHandler(OnProcessStart(target_action=spawn, on_start=[spawner_jsb]))
    diff_on_jsb = RegisterEventHandler(OnProcessStart(target_action=spawner_jsb, on_start=[spawner_diff]))

    # LaunchSÌ\¬
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("verbose", default_value="false"),
        DeclareLaunchArgument("model_name", default_value="megarover3"),
        rsp,
        make_world,
        gazebo_launch,
        spawn,
        jsb_on_spawn,
        diff_on_jsb,
        relay_node,
    ])

