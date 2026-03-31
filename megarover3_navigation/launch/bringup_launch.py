from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    nav_launch = os.path.join(
        get_package_share_directory('megarover3_navigation'),
        'launch',
        'navigation.launch.py',
    )

    return LaunchDescription([
        DeclareLaunchArgument('rover', default_value='mega3'),
        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('use_namespace', default_value='false'),
        DeclareLaunchArgument('slam', default_value='False'),
        DeclareLaunchArgument('map', default_value=''),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('params_file', default_value=''),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument('use_composition', default_value='True'),
        DeclareLaunchArgument('container_name', default_value='nav2_container'),
        DeclareLaunchArgument('use_respawn', default_value='False'),
        DeclareLaunchArgument('log_level', default_value='info'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(
                get_package_share_directory('megarover3_navigation'),
                'config',
                'mapper_params_online_async.yaml',
            ),
        ),

        LogInfo(msg='[bringup_launch] navigation.launch.py を起動します'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav_launch),
            launch_arguments={
                'rover': LaunchConfiguration('rover'),
                'namespace': LaunchConfiguration('namespace'),
                'use_namespace': LaunchConfiguration('use_namespace'),
                'slam': LaunchConfiguration('slam'),
                'map': LaunchConfiguration('map'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'params_file': LaunchConfiguration('params_file'),
                'autostart': LaunchConfiguration('autostart'),
                'use_composition': LaunchConfiguration('use_composition'),
                'container_name': LaunchConfiguration('container_name'),
                'use_respawn': LaunchConfiguration('use_respawn'),
                'log_level': LaunchConfiguration('log_level'),
                'slam_params_file': LaunchConfiguration('slam_params_file'),
                'use_rviz': 'false',
            }.items(),
        ),
    ])
