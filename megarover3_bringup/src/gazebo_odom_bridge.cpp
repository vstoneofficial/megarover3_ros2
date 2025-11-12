#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    cmd_topic    = LaunchConfiguration('cmd_topic',    default='/rover_twist')
    model_name   = LaunchConfiguration('model_name',   default='mega3')
    scan_topic   = LaunchConfiguration('scan_topic',   default='/scan')
    odom_frame   = LaunchConfiguration('odom_frame',   default='odom')
    base_frame   = LaunchConfiguration('base_frame',   default='base_footprint')

    pkg_desc  = get_package_share_directory('megarover_description')
    pkg_bring = get_package_share_directory('megarover3_bringup')
    pkg_nav   = get_package_share_directory('megarover3_navigation')
    pkg_gzb   = get_package_share_directory('megarover3_gazebo')

    # Gazebo bringup
    gazebo_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([PathJoinSubstitution([pkg_gzb, 'launch', 'gazebo_bringup.launch.py'])]),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # SLAM launch
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([PathJoinSubstitution([pkg_nav, 'launch', 'slam.launch.py'])]),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('cmd_topic',    default_value='/rover_twist'),
        DeclareLaunchArgument('model_name',   default_value='mega3'),
        DeclareLaunchArgument('scan_topic',   default_value='/scan'),
        DeclareLaunchArgument('odom_frame',   default_value='odom'),
        DeclareLaunchArgument('base_frame',   default_value='base_footprint'),
        gazebo_bringup,
        slam_launch,
    ])

