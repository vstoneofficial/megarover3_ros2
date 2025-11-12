#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    pkg_gzb = get_package_share_directory('megarover3_gazebo')
    pkg_nav = get_package_share_directory('megarover3_navigation')

    # Gazebo world and robot spawner
    gazebo_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([pkg_gzb, 'launch', 'gazebo_bringup.launch.py'])]
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # Wall object
    spawn_wall = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([pkg_gzb, 'launch', 'spawn_wall.launch.py'])]
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # Wait until /clock topic is available
    wait_clock = ExecuteProcess(
        cmd=['/bin/bash', '-c',
             "until ros2 topic list | grep -q '/clock'; do sleep 1; done; echo '[clock] [OK]' > /dev/null"]
    )

    # Wait until odom topic is available
    wait_odom = ExecuteProcess(
        cmd=['/bin/bash', '-c',
             "until ros2 topic list | grep -q '/diff_drive_controller/odom'; do sleep 1; done; echo '[odom] [OK]' > /dev/null"]
    )

    # Wait until TF (odom->base_footprint) is available
    wait_tf = ExecuteProcess(
        cmd=['/bin/bash', '-c',
             "until ros2 run tf2_ros tf2_echo odom base_footprint --once >/dev/null 2>&1; do sleep 1; done; echo '[tf odom->base_footprint] [OK]' > /dev/null"]
    )

    # SLAM launch (slam_toolbox)
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [PathJoinSubstitution([pkg_nav, 'launch', 'slam.launch.py'])]
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items()
    )

    # Display remap info once
    check_remap = ExecuteProcess(
        cmd=['/bin/bash', '-c',
             "echo '[Remap] /cmd_vel → /rover_twist (for Gazebo robot control)' > /dev/null"],
        shell=True,
        output='log'
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        gazebo_bringup,
        spawn_wall,
        wait_clock,
        wait_odom,
        wait_tf,
        check_remap,
        slam_launch,
    ])

