from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'my_package_py'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='changes',
    maintainer_email='changes@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'motor_controller = my_package_py.motor_controller_node:main',
            'keyboard_control = my_package_py.keyboard_control:main',
            'chassis_controller = my_package_py.chassis_speed_controller:main',
        ],
    },
)
