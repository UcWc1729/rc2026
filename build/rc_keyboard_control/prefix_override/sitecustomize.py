import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/ljhua/ROBOCON2026/lidar_test/rc2026/install/rc_keyboard_control'
