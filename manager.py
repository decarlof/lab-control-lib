"""
Manage driver and daemon creation.
"""

import logging
import subprocess
import time
import sys

from .ui_utils import ask_yes_no
from .base import DaemonException
from . import network_conf
from . import mecademic
from . import smaract
from . import mclennan
from . import aerotech
from . import excillum
from . import dummy

DRIVER_DATA  = {'mecademic': {'driver': mecademic.Mecademic},
                'smaract': {'driver': smaract.Smaract},
                'aerotech': {'driver': aerotech.Aerotech},
                'mclennan1': {'driver': mclennan.McLennan,
                              'daemon_address': network_conf.MCLENNAN1['DAEMON'],
                              'name': 'mclennan1'},
                'mclennan2': {'driver': mclennan.McLennan,
                              'daemon_address': network_conf.MCLENNAN2['DAEMON'],
                              'name': 'mclennan2'},
                'excillum': {'driver': excillum.Excillum},
                'dummy': {'driver': dummy.Dummy}
              # 'xps': {},
              # 'pco': {},
              # 'varex': {},
              # 'xspectrum': {},
                }

logger = logging.getLogger("manager")


def instantiate_driver(driver, daemon_address=None, name=None, admin=True, spawn=True):
    """
    Helper function to instantiate a driver and
    spawning the corresponding daemon if necessary and requested.
    """
    if name is None:
        name = driver.__name__.lower()

    # Try to instantiate the driver:
    d = None
    try:
        d = driver(address=daemon_address, name=name, admin=admin)
    except DaemonException:
        if not spawn:
            logger.warning(f'Daemon for driver {name} unreachable')
            return None

        # Didn't connect. Let's try to spawn the Daemon.
        if ask_yes_no('Daemon unreachable. Spawn it?'):
            p = subprocess.Popen([sys.executable, '-m', 'labcontrol.startup', 'start', f'{name}'],
                                 start_new_session=True,)
                               # stdout=subprocess.DEVNULL,
                               # stderr=subprocess.STDOUT)
            logger.info(f'Deamon process {name} spawned.')
            # Make sure the daemon is already listening before connecting
            time.sleep(20)
            d = driver(address=daemon_address)
        else:
            logger.error(f'Driver {driver.name} is not running.')
    return d

