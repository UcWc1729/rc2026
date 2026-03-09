from setuptools import setup
from setuptools import find_packages

package_name = 'rc_serial_driver'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/serial_driver.launch.py']),
        ('share/' + package_name + '/config', ['config/serial_driver_params.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='fyt',
    maintainer_email='fyt@todo.todo',
    description='Serial driver for communication with lower computer (下位机串口驱动)',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'serial_driver_node = rc_serial_driver.serial_driver_node:main',
        ],
    },
)
