#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def _gen_sdf_and_spawn(context, *args, **kwargs):
    # --- Read launch-time parameters (strings) and convert types where needed
    entity  = LaunchConfiguration('entity').perform(context)
    static  = LaunchConfiguration('static').perform(context).lower() == 'true'
    units   = LaunchConfiguration('units').perform(context).lower()           # 'mm' or 'm'
    mesh_uri_in = LaunchConfiguration('mesh_uri').perform(context)           # '' | 'auto' | explicit URI

    # Scale comes as "sx,sy,sz"
    sx, sy, sz = LaunchConfiguration('scale').perform(context).split(',')
    x     = float(LaunchConfiguration('x').perform(context))
    y     = float(LaunchConfiguration('y').perform(context))
    z     = float(LaunchConfiguration('z').perform(context))
    roll  = float(LaunchConfiguration('roll').perform(context))
    pitch = float(LaunchConfiguration('pitch').perform(context))
    yaw   = float(LaunchConfiguration('yaw').perform(context))

    if mesh_uri_in == '' or mesh_uri_in.lower() == 'auto':
        pkg_share = get_package_share_directory('megarover3_gazebo')
        wall_path = os.path.join(pkg_share, 'models', 'Wall1.stl')
        mesh_uri  = f'file://{wall_path}'
    else:
        mesh_uri = mesh_uri_in

    if units == 'mm':
        sx, sy, sz = str(float(sx)*0.001), str(float(sy)*0.001), str(float(sz)*0.001)

    print(f"[spawn_wall] entity={entity} mesh_uri={mesh_uri} "
          f"scale=({sx},{sy},{sz}) static={static} "
          f"pose=({x},{y},{z}; {roll},{pitch},{yaw})")

    sdf = f'''<?xml version="1.0" ?>
<sdf version="1.6">
  <model name="{entity}">
    <static>{str(static).lower()}</static>
    <link name="walls_link">
      <pose>0 0 0 0 0 0</pose>
      <collision name="col">
        <geometry>
          <mesh>
            <uri>{mesh_uri}</uri>
            <scale>{sx} {sy} {sz}</scale>
          </mesh>
        </geometry>
      </collision>
      <visual name="vis">
        <geometry>
          <mesh>
            <uri>{mesh_uri}</uri>
            <scale>{sx} {sy} {sz}</scale>
          </mesh>
        </geometry>
        <material>
          <ambient>0.8 0.8 0.8 1</ambient>
          <diffuse>0.8 0.8 0.8 1</diffuse>
        </material>
      </visual>
    </link>
  </model>
</sdf>
'''
    tmpdir = tempfile.mkdtemp(prefix='spawn_wall_')
    sdf_path = os.path.join(tmpdir, f'{entity}.sdf')
    with open(sdf_path, 'w') as f:
        f.write(sdf)
        
    return [Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', entity,
            '-file', sdf_path,
            '-x', str(x), '-y', str(y), '-z', str(z),
            '-R', str(roll), '-P', str(pitch), '-Y', str(yaw),
        ],
        output='log'
    )]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'mesh_uri', default_value='',
            description='STL URI (e.g., file:///abs/path/model.stl). '
                        'Empty or "auto" resolves to packaged Wall1.stl'
        ),
        DeclareLaunchArgument('entity', default_value='wall_1', description='Gazebo model name'),
        DeclareLaunchArgument('static', default_value='true', description='Spawn as Gazebo static model'),
        DeclareLaunchArgument('units',  default_value='mm', description='Input mesh units: "mm" or "m"'),
        DeclareLaunchArgument('scale',  default_value='1,1,1', description='Extra scale factors "sx,sy,sz"'),
        DeclareLaunchArgument('x', default_value='-0.75', description='Spawn X [m]'),
        DeclareLaunchArgument('y', default_value='-0.75', description='Spawn Y [m]'),
        DeclareLaunchArgument('z', default_value='0.0',   description='Spawn Z [m]'),
        DeclareLaunchArgument('roll',  default_value='0.0', description='Roll [rad]'),
        DeclareLaunchArgument('pitch', default_value='0.0', description='Pitch [rad]'),
        DeclareLaunchArgument('yaw',   default_value='0.0', description='Yaw [rad]'),
        OpaqueFunction(function=_gen_sdf_and_spawn),
    ])

