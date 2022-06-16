"""
Mecademic meca500 interface

TODO: more documentation here.

TODO: how to deal with pseudomotors.
Especially: pseudo motors that emulate translation of the sample
wrt the axis of rotation.

TODO: how to better define "free moving zones".


"""
import logging
import time
import socket
import os
import threading
import select

from .base import MotorBase, DriverBase, SocketDeviceServerBase, admin_only, emergency_stop, DeviceException, _recv_all
from .network_conf import MECADEMIC as DEFAULT_NETWORK_CONF
from .ui_utils import ask_yes_no
from . import conf_path

__all__ = ['MecademicDaemon', 'Mecademic']#, 'Motor']

# This API uses null character (\0) as end-of-line.
EOL = b'\0'

# Default joint velocity: 5% of maximum ~= 18 degrees / s
DEFAULT_VELOCITY = 5

MAX_JOINT_VELOCITY = [150., 150., 180., 300., 300., 500.]


class RobotException(Exception):
    def __init__(self, code, message=''):
        self.code = code
        self.message = f'{code}: {message}'
        super().__init__(self.message)


class MecademicMonitor():
    """
    Light weight class that connects to the monitor port.
    """

    EOL = EOL
    DEFAULT_MONITOR_ADDRESS = DEFAULT_NETWORK_CONF['MONITOR']
    MONITOR_TIMEOUT = 1
    NUM_CONNECTION_RETRY = 10
    MAX_BUFFER_LENGTH = 1000

    def __init__(self, monitor_address=None):

        if monitor_address is None:
            monitor_address = self.DEFAULT_MONITOR_ADDRESS

        self.logger = logging.getLogger(self.__class__.__name__)

        # Store device address
        self.monitor_address = monitor_address
        self.monitor_sock = None

        # Buffer in which incoming data will be stored
        self.recv_buffer = None
        # Flag to inform other threads that data has arrived
        self.recv_flag = None
        # Listening/receiving thread
        self.recv_thread = None

        # dict of received messages (key is message code)
        self.messages = {}

        self.callbacks = {}

        self.shutdown_requested = False

        # Connect to device
        self.connected = False
        self.connect_device()

    def connect_device(self):
        """
        Device connection
        """
        # Prepare device socket connection
        self.monitor_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP socket
        self.monitor_sock.settimeout(self.MONITOR_TIMEOUT)

        for retry_count in range(self.NUM_CONNECTION_RETRY):
            conn_errno = self.monitor_sock.connect_ex(self.monitor_address)
            if conn_errno == 0:
                break

            self.logger.critical(os.strerror(conn_errno))
            time.sleep(.05)

        if conn_errno != 0:
            self.logger.critical("Can't connect to device")
            raise DeviceException("Can't connect to device")

        # Start receiving data
        self.recv_buffer = b''
        self.recv_flag = threading.Event()
        self.recv_flag.clear()
        self.recv_thread = threading.Thread(target=self._listen_recv)
        self.recv_thread.daemon = True
        self.recv_thread.start()

        self.connected = True

    def _listen_recv(self):
        """
        This threads receives all data in real time and stores it
        in a local buffer. For devices that send data only after
        receiving a command, the buffer is read and emptied immediately.
        """
        while True:
            if self.shutdown_requested:
                break
            d = _recv_all(self.monitor_sock, EOL=self.EOL)
            self.recv_buffer += d
            self.consume_buffer()

    def consume_buffer(self):
        """
        Parse buffered messages - running on the same thread as _listen_recv.
        """
        tokens = self.recv_buffer.split(EOL)
        for t in tokens:
            ts = t.decode('ascii', errors='ignore')
            code, message = ts.strip('[]').split('][')
            code = int(code)
            if not self.messages.get(code):
                self.messages[code] = []
            self.messages[code].append(message)
            if len(self.messages[code] > self.MAX_BUFFER_LENGTH):
                self.messages[code].pop(0)
            self.callbacks.get(code, lambda m: None)(message)
        self.recv_buffer = b''


class MecademicDaemon(SocketDeviceServerBase):
    """
    Mecademic Daemon, keeping connection with Robot arm.
    """

    DEFAULT_SERVING_ADDRESS = DEFAULT_NETWORK_CONF['DAEMON']
    DEFAULT_DEVICE_ADDRESS = DEFAULT_NETWORK_CONF['DEVICE']
    EOL = EOL
    KEEPALIVE_INTERVAL = 60

    def __init__(self, serving_address=None, device_address=None):
        if serving_address is None:
            serving_address = self.DEFAULT_SERVING_ADDRESS
        if device_address is None:
            device_address = self.DEFAULT_DEVICE_ADDRESS
        super().__init__(serving_address=serving_address, device_address=device_address)

    def init_device(self):
        """
        Device initialization.
        """
        # ask for firmware version to see if connection works
        version = self.device_cmd(b'GetFwVersion' + self.EOL)
        version = version.decode('ascii').strip()
        self.logger.debug(f'Firmware version is {version}')

        self.initialized = True
        return

    def wait_call(self):
        """
        Keep-alive call
        """
        r = self.device_cmd(b'GetStatusRobot' + self.EOL)
        if not r:
            raise DeviceException


class Mecademic(DriverBase):
    """
    Driver for the Meca500 robot arm

    TODO: a good way to define limits, ranges, etc.
    """

    EOL = EOL
    POLL_INTERVAL = 0.01     # temporization for rapid status checks during moves.

    DEFAULT_JOINT_POSITION = (0.0,
                              -20.37038014,
                              16.28988378,
                              0.0,
                              -(90 + -20.37038014 + 16.28988378),
                              0.0)

    # theta 1 range can be quite dangerous.
    # Undocumented feature: all limit ranges have to be at least 30 degree wide.
    DEFAULT_JOINT_LIMITS = ((-15., 15.),
                            (-21., 17.),
                            (-45, 15),
                            (-15., 15.),
                            (-112., -24),
                            (-360., 360.))

    def __init__(self, address=None, admin=True):
        """
        Initialise Mecademic driver (robot arm).
        """
        if address is None:
            address = DEFAULT_NETWORK_CONF['DAEMON']

        super().__init__(address=address, admin=admin)

        self.metacalls.update({'pose': self.get_pose,
                               'joints': self.get_joints,
                               'status': self.get_status})

        self.last_error = None
        self.motion_paused = False

        self.initialize()

    @admin_only
    def initialize(self):
        """
        First commands after connections.

        Will probably be refined depending on how the robot is used.
        """
        # Set time
        self.set_RTC()

        # 1. Check current state and prompt for activation/homing
        #########################################################
        status = self.get_status()
        if status[3]:
            # Error mode
            if ask_yes_no('Robot in error mode. Clear?'):
                self.clear_error()
            else:
                self.logger.warning('Robot still in error mode after driver initialization.')
                return
        if not status[0]:
            if ask_yes_no('Robot deactivated. Activate?'):
                self.activate()
            else:
                self.logger.warning('Robot not activated after driver initialization')
                return
        if not status[1]:
            # Not homed
            if ask_yes_no('Robot not homed. Home?'):
                self.home()
            else:
                self.logger.warning('Robot not homed after driver initialization.')
                return

        self.logger.info("Initialization complete.")

    def send_cmd(self, cmd, args=None):
        """
        Send properly formatted request to the driver
        and parse the reply.
        Replies from the robot are of the form [code][data].
        This method returns a list of tuples (int(code), data)

        args, if not none is tuple of arguments to pass as arguments
        to the command.

        cmd can be a single string, or a list of strings if multiple
        commands are to be sent in a batch. In this case, args
        should be a list of the same length.
        """
        # This looks complicated because we need to manage the
        # case of multiple commands. So in the case of single command.
        # we convert to a list with a single element.
        if isinstance(cmd, str):
            cmds = [cmd.encode()]
            args = [args]
        else:
            cmds = [c.encode() for c in cmd]
            if len(cmds) != len(args):
                raise RuntimeError('Length of command and args lists differ.')

        # Format arguments
        cmd = b''
        for c, arg in zip(cmds, args):
            cmd += c
            if arg is not None:
                try:
                    arg = tuple(arg)
                except TypeError:
                    arg = (arg, )
                cmd += f'{arg}'.encode()
            cmd += self.EOL
        reply = self.send_recv(cmd)
        return self.process_reply(reply)

    def process_reply(self, reply):
        """
        Take care of stripping and splitting raw reply from device
        Raise error if needed.
        """
        # First split along EOL in case there are more than one reply
        raw_replies = reply.split(self.EOL)
        # Convert each
        formatted_replies = []
        for r in raw_replies:
            r_str = r.decode('ascii', errors='ignore')
            code, message = r_str.strip('[]').split('][')
            code = int(code)
            formatted_replies.append((code, message))

        # Manage errors and other strange things here
        reply2000 = None
        for code, message in formatted_replies:
            if code == 2042:
                # Motion paused - not useful
                self.motion_paused = True
            elif code < 2000:
                # Error code.
                self.last_error = (code, message)
                self.logger.error(f'[{code}] - {message}')
            elif code > 2999:
                # Status message sent "out of the blue"
                self.logger.warning(f'{code}: {message}')
            else:
                rep = (code, message)
                if reply2000 is not None:
                    # This should not happen
                    self.logger.warning(f'More code 2000:{reply2000[0]} - {reply2000[1]}')
                reply2000 = rep

        # Manage cases where the only reply is e.g. a 3000
        if reply2000 is None:
            reply2000 = None, None
        return reply2000

    @admin_only
    def set_TRF_at_wrist(self):
        """
        Sets the Tool reference frame at the wrist of the robot (70 mm below the
        flange). This makes all pose changes much easier to understand and predict.

        This is not a good solution when the center of rotation has so be above the
        flange (e.g. to keep a sample in place).
        """
        code, reply = self.send_cmd('SetTRF', (0, 0, -70, 0, 0, 0))

    def get_status(self):
        """
        Get robot current status

        From documentation:
        [2007][as, hs, sm, es, pm, eob, eom]
        as: activation state (1 if robot is activated, 0 otherwise);
        hs: homing state (1 if homing already performed, 0 otherwise);
        sm: simulation mode (1 if simulation mode is enabled, 0 otherwise);
        es: error status (1 for robot in error mode, 0 otherwise);
        pm: pause motion status (1 if robot is in pause motion, 0 otherwise);
        eob: end of block status (1 if robot is idle and motion queue is empty, 0 otherwise);
        eom: end of movement status (1 if robot is idle, 0 if robot is moving).
        """
        code, reply = self.send_cmd('GetStatusRobot')
        try:
            status = [bool(int(x)) for x in reply.split(',')]
        except:
            self.logger.error(f'get_status returned {reply}')
            status = None
        return status

    @admin_only
    def set_RTC(self, t=None):
        """
        Set time. Not clear if there's a reason to set something else
        than current time...
        """
        if t is None:
            t = time.time()
        # Not documented, but setRTC actually sends a reply,
        # So no need to send two commands
        code, message = self.send_cmd('SetRTC', t)
        return

    @admin_only
    def home(self):
        """
        Home the robot
        """
        code, reply = self.send_cmd('Home')
        if code == 2003:
            # Already homed
            self.logger.warning(reply)
        else:
            self.logger.info(reply)
        return

    @admin_only
    def activate(self):
        """
        Activate the robot
        """
        code, reply = self.send_cmd('ActivateRobot')
        if code == 2001:
            # Already activated
            self.logger.warning(reply)
        else:
            self.logger.info(reply)
        return

    @admin_only
    def activate_sim(self):
        """
        Activate simulation mode
        """
        code, reply = self.send_cmd('ActivateSim')

    @admin_only
    def deactivate_sim(self):
        """
        Activate simulation mode
        """
        code, reply = self.send_cmd('DeactivateSim')

    @admin_only
    def deactivate(self):
        """
        Deactivate the robot
        """
        code, reply = self.send_cmd('DeactivateRobot')
        self.logger.info(reply)
        return

    @admin_only
    def clear_errors(self):
        """
        Clear error status.
        """
        code, reply = self.send_cmd('ResetError')
        if code == 2006:
            # Already activated
            self.logger.warning(reply)
        else:
            self.logger.info(reply)
        return

    @admin_only
    def set_joint_velocity(self, p):
        """
        Set joint velocity as a percentage of the maximum speed.
        (See MAX_JOINT_VELOCITY)

        The last is especially important for continuous tomographic scans.
        """
        code, reply = self.send_cmd('SetJointVel', p)

    @admin_only
    def move_joints(self, joints, block=True):
        """
        Move joints
        """
        # Send two commands because 'MoveJoints' doesn't immediately
        # return something
        status = self.get_status()
        if status[2]:
            self.logger.warning('simulation mode')
        code, reply = self.send_cmd(['MoveJoints', 'GetStatusRobot'], [joints, None])
        if block:
            self.check_done()
        else:
            self.logger.info('Non-blocking motion started.')
        return self.get_joints()

    @admin_only
    def move_single_joint(self, angle, joint_number, block=True):
        """
        Move a single joint to given angle.
        """
        # Send two commands because 'MoveJoints' doesn't immediately
        # return something
        status = self.get_status()
        if status[2]:
            self.logger.warning('simulation mode')
        # Get current joints and change only one value
        joints = self.get_joints()
        joints[joint_number - 1] = angle

        # Ask to move
        code, reply = self.send_cmd(['MoveJoints', 'GetStatusRobot'], [joints, None])
        if block:
            self.check_done()
        else:
            self.logger.info('Non-blocking motion started.')
        return self.get_joints()

    def rotate_continuous(self, end_angle, duration, start_angle=None, joint_number=6, block=False):
        """
        Rotate one joint (by default 6th) from start_angle (by default current)
        to given end_angle, setting the joint velocity for the rotation to last
        given duration.

        NOTE: This function is non-blocking by default
        """
        # Move to start.
        self.move_single_joint(start_angle, joint_number=joint_number)

        # Velocity in degrees / seconds
        vel = abs(end_angle - start_angle)/duration

        # Percentage of maximum velocity
        p = 100 * vel/MAX_JOINT_VELOCITY[joint_number-1]
        self.logger.info(f'Setting velocity of joint {joint_number} to {vel:0.3f} degrees/seconds (p = {p})')
        self.set_joint_velocity(p)

        # Now start move
        self.move_single_joint(end_angle, joint_number=joint_number, block=block)

    def get_joints(self):
        """
        Get current joint angles.

        The manual says that GetRtJointPos is better than GetJoints
        """
        code, reply = self.send_cmd('GetRtJointPos')
        joints = [float(x) for x in reply.split(',')]
        # Drop the first element (timestamp)
        return joints[1:]

    @admin_only
    def move_pose(self, pose):
        """
        Move to pose given by coordinates (x,y,z,alpha,beta,gamma)
        """
        # Send two commands because 'MovePose' doesn't immediately
        # return something
        status = self.get_status()
        if status[2]:
            self.logger.warning('simulation mode')
        code, reply = self.send_cmd(['MovePose', 'GetStatusRobot'], [pose, None])
        self.check_done()
        return self.get_pose()

    def get_pose(self):
        """
        Get current pose (x,y,z, alpha, beta, gamma)
        """
        code, reply = self.send_cmd('GetRtCartPos')
        pose = [float(x) for x in reply.split(',')]
        # Drop the first element (timestamp)
        return pose[1:]

    def check_done(self):
        """
        Poll until movement is complete.

        Implements emergency stop
        """
        with emergency_stop(self.abort):
            while True:
                # query axis status
                status = self.get_status()
                if status is None:
                    continue
                if status[6]:
                    break
                # Temporise
                time.sleep(self.POLL_INTERVAL)
        self.logger.info("Finished moving robot.")

    @admin_only
    def move_to_default_position(self):
        """
        Move to the predefined default position.

        TODO: maybe we will have more than one of those.
        """
        self.move_joints(self.DEFAULT_JOINT_POSITION)

    def get_joint_limits(self):
        """
        Get current joint limits.
        """
        limits = []
        for i in range(6):
            code, message = self.send_cmd('GetJointLimits', i+1)
            # message is of the form n, low, high
            s = message.split(',')
            limits.append((float(s[1]), float(s[2])))
        return limits

    @admin_only
    def set_joint_limits(self, limits):
        """
        Set joint limits. This must be done while robot is not active,
        so can be complicated.

        Since this is a critical operation, the user is prompted,
        and the default is no.
        """
        self.logger.critical("changing joint limits is a risky and rare operation. This function is currently disabled.")

        """        
        if self.isactive:
            prompt = 'Robot is active. Deactivate?'

        # Enable custom joint limits
        code, reply = self.send_cmd('SetJointLimitsCfg', 1)

        # Check if limits are already set
        current_limits = self.get_joint_limits()
        if np.allclose(current_limits, limits, atol=.1):
            self.logger.info("Limits are already set.")
            return

        # Ask user to confirm
        prompt = 'Preparing to change joint limits as follows:\n'
        for i, (low, high) in enumerate(limits):
            prompt += f' * theta {i+1}: ({low:9.5f}, {high:9.5f})\n'
        prompt += 'Are you sure you want to proceed?'
        if not ask_yes_no(prompt, yes_is_default=False):
            self.logger.error('Setting limit cancelled.')
            return

        for i, (low, high) in enumerate(limits):
            code, message = self.send_cmd('SetJointLimits', (i+1, low, high))

        self.logger.info("Joint limits have been changed.")
        """

        return

    def abort(self):
        """
        Abort current motion.

        TODO: check what happens if this is called while robot is idle.
        """
        # Abort immediately
        self.logger.warning('Aborting robot motion!')
        code, message = self.send_cmd('ClearMotion')

        # Ready for next move
        code, message = self.send_cmd('ResumeMotion')

    @property
    def isactive(self):
        return self.get_status()[0] == 1

    @property
    def ishomed(self):
        return self.get_status()[1] == 1


class Motor(MotorBase):
    def __init__(self, name, driver, axis):
        super(Motor, self).__init__(name, driver)
        self.axis = ['x', 'z', 'y', 'tilt', 'roll', 'rot'].index(axis)

        # Convention for the lab is y up, z along propagation
        if self.axis == 1:
            self.scalar = -1.

    def _get_pos(self):
        """
        Return position in mm
        """
        return self.driver.get_pose()[self.axis]

    def _set_abs_pos(self, x):
        """
        Set absolute position
        """
        pose = self.driver.get_pose()
        pose[self.axis] = x
        new_pose = self.driver.move_pose(pose)
        return new_pose[self.axis]