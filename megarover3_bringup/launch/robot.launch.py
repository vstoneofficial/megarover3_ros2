# Example usage:
# Arguments (pass arguments as '<name>:=<value>'):
#
#     'rover':
#         model of rover robot. Valid choices are: 'mega3', 'f120a'
#         (default: 'mega3')
#
#     'option':
#         options for robot. Valid choices are: '', '_lrf', '_depthcam', '_lrf_depthcam', '_bumper'
#         (default: '')
#
# mega3 + lrf:
# ros2 launch megarover3_bringup robot.launch.py rover:=mega3 option:=_lrf
# f120a + lrf + depthcam:
# ros2 launch megarover3_bringup robot.launch.py rover:=f120a option:=_lrf_depthcam

import os
import yaml
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, Command

from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from ament_index_python.packages import get_package_share_directory
from launch_ros.parameter_descriptions import ParameterValue

from launch.conditions import LaunchConfigurationEquals

configurable_parameters = [
    {'name': 'rover',       'default': 'mega3', 'description': 'model of rover', 'choices': "'mega3', 'f120a'"},
    {'name': 'option',      'default': '',      'description': 'options for rover',    'choices': "'', '_lrf', '_depthcam', '_lrf_depthcam', '_bumper'"},
    #    {'name': 'config_file',      'default': "''",'description': 'yaml config file', 'choices': "''"},
]


def declare_configurable_parameters(parameters):
    return [DeclareLaunchArgument(param['name'], default_value=param['default'], description=param['description'], choices=param['choices']) for param in parameters]


def set_configurable_parameters(parameters):
    return dict([(param['name'], LaunchConfiguration(param['name'])) for param in parameters])


# def yaml_to_dict(path_to_yaml):
#     with open(path_to_yaml, "r") as f:
#         return yaml.load(f, Loader=yaml.SafeLoader)


def launch_setup(context, params, param_name_suffix=''):
    # _config_file = LaunchConfiguration(
    #     'config_file' + param_name_suffix).perform(context)
    # params_from_file = {} if _config_file == "''" else yaml_to_dict(
    #     _config_file)

    rover_type_str = LaunchConfiguration('rover').perform(context)
    option_type_str = LaunchConfiguration('option').perform(context)

    robot_description_path = os.path.join(
        get_package_share_directory('megarover_description'),
        'urdf',
        f'{rover_type_str}{option_type_str}.xacro'
    )
    rviz_config_path = os.path.join(
        get_package_share_directory('megarover3_bringup'),
        'rviz',
        f'{rover_type_str}.rviz'
    )

    return [
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher_node',
            parameters=[{'robot_description': ParameterValue(
                    Command(['xacro ', str(robot_description_path)]), value_type=str
            )}]
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='mega3_rviz2',
            output='screen',
            arguments=['-d', rviz_config_path],
        ),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
        ),

        Node(
            package='megarover3_bringup',
            executable='pub_odom',
            name='pub_odom'
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(get_package_share_directory('megarover3_bringup'), 'launch', 'ydlidar_tg30_launch.py')),
            condition=LaunchConfigurationEquals('option', '_lrf'),
        ),


    ]


def generate_launch_description():
    return LaunchDescription(declare_configurable_parameters(configurable_parameters) + [
        OpaqueFunction(function=launch_setup, kwargs={
                       'params': set_configurable_parameters(configurable_parameters)})
    ])
