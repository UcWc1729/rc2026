import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/changes/2026ROBOCON/Task/Serial_test/Serial_ws/install/my_package_py'
