from setuptools import setup
import os
from glob import glob

package_name = 'rc_keyboard_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='fyt',
    maintainer_email='fyt@todo.todo',
    description='Keyboard control node for robot chassis',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'keyboard_control_node = rc_keyboard_control.keyboard_control_node:main',
        ],
    },
)
