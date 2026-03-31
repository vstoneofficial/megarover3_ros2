import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


CONFIGURABLE_PARAMETERS = [
    {
        'name': 'rover',
        'default': 'mega3',
        'description': 'model of rover',
        'choices': "'mega3', 'f120a', 's40a_lb'",
    },
]


def declare_configurable_parameters(parameters):
    return [
        DeclareLaunchArgument(
            param['name'],
            default_value=param['default'],
            description=param['description'],
            choices=param['choices'],
        )
        for param in parameters
    ]


def set_configurable_parameters(parameters):
    return {param['name']: LaunchConfiguration(param['name']) for param in parameters}


def launch_setup(context, params, param_name_suffix=''):
    rover_type = LaunchConfiguration('rover').perform(context)

    robot_description_path = os.path.join(
        get_package_share_directory('megarover_description'),
        'urdf',
        f'{rover_type}.xacro',
    )
    rviz_config_path = os.path.join(
        get_package_share_directory('megarover3_bringup'),
        'rviz',
        f'{rover_type}.rviz',
    )

    return [
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher_node',
            parameters=[
                {
                    'robot_description': ParameterValue(
                        Command(['xacro ', robot_description_path]),
                        value_type=str,
                    )
                }
            ],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='megarover_rviz2',
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
            name='pub_odom',
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        declare_configurable_parameters(CONFIGURABLE_PARAMETERS)
        + [
            OpaqueFunction(
                function=launch_setup,
                kwargs={'params': set_configurable_parameters(CONFIGURABLE_PARAMETERS)},
            )
        ]
    )
