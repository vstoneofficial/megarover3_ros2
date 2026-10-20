import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    parameters = os.path.join(
        get_package_share_directory('megarover3_navigation'),
        'config', 'mapper_params_online_async.yaml',
    )
    return LaunchDescription([
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument(
            'use_lifecycle_manager', default_value='false',
            description='External manager owns transitions; disables launch autostart.',
        ),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('slam_params_file', default_value=parameters),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('slam_toolbox'),
                'launch', 'online_async_launch.py',
            )),
            launch_arguments={
                name: LaunchConfiguration(name) for name in (
                    'autostart', 'use_lifecycle_manager', 'use_sim_time', 'slam_params_file',
                )
            }.items(),
        ),
    ])
