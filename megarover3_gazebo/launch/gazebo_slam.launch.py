#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    # --------------------------------------------------
    # Launch arguments
    # --------------------------------------------------
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    rover        = LaunchConfiguration('rover', default='mega3')
    wall         = LaunchConfiguration('wall', default='Wall.stl')

    # --------------------------------------------------
    # Package paths
    # --------------------------------------------------
    pkg_gzb = get_package_share_directory('megarover3_gazebo')
    pkg_nav = get_package_share_directory('megarover3_navigation')

    # --------------------------------------------------
    # RViz config (passed to SLAM launch)
    # --------------------------------------------------
    rviz_config = LaunchConfiguration(
        'rvizconfig',
        default=PathJoinSubstitution([
            pkg_nav, 'rviz', 'slam.rviz'
        ])
    )

    # --------------------------------------------------
    # Gazebo bringup (world + robot only)
    # --------------------------------------------------
    gazebo_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                pkg_gzb,
                'launch',
                'gazebo_bringup.launch.py'
            ])
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'rover': rover,
        }.items()
    )

    # --------------------------------------------------
    # Wall spawn (static, fixed pose, STL by name)
    # --------------------------------------------------
    spawn_wall = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                pkg_gzb,
                'launch',
                'spawn_wall.launch.py'
            ])
        ),
        launch_arguments={
            'wall': wall,
        }.items()
    )

    # --------------------------------------------------
    # SLAM (shared lower-level launch, do not modify)
    # --------------------------------------------------
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                pkg_nav,
                'launch',
                'slam.launch.py'
            ])
        ),
        launch_arguments={
            'rvizconfig': rviz_config,
        }.items()
    )

    # --------------------------------------------------
    # Launch description
    # --------------------------------------------------
    return LaunchDescription([

        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true'
        ),

        DeclareLaunchArgument(
            'rover',
            default_value='mega3',
            description='Rover type (mega3, f120a, s40a_lb)'
        ),

        DeclareLaunchArgument(
            'wall',
            default_value='Wall.stl',
            description='Wall STL filename under megarover3_gazebo/models'
        ),

        DeclareLaunchArgument(
            'rvizconfig',
            default_value=PathJoinSubstitution([
                pkg_nav, 'rviz', 'slam.rviz'
            ])
        ),

        gazebo_bringup,
        spawn_wall,
        slam,
    ])

