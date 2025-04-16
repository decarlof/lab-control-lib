"""
Management of experiment data, scans, labeling, etc.

The scan structure is inspired from Elettra's storage structure
 * Investigation: highest category (e.g. speckle_long_branch)
 * Experiment: Typically an experiment run (over days, possibly in multiple parts)
 * Scan: (instead of Elettra's "dataset") a numbered (and possibly labeled) dataset

This file is part of lab-control-lib
(c) 2023-2024 Pierre Thibault (pthibault@units.it)
"""

import os
from datetime import datetime

from . import proxycall, proxydevice

from .util import now
from .base import DriverBase

__all__ = ['list_investigations', 'list_scans', 'ManagerBase']

def list_investigations(path):
    """
    List all investigations (directories in  base path)
    Args:
        path: base path

    Returns:
        list of investigations
    """
    return [f.name for f in os.scandir(path) if f.is_dir() and not f.name.startswith('.')]

def list_scans(path, investigation, experiment=None, logger=None):
    """
    List all scans in given experiment (all experiments if None)
    Args:
        path: base path
        investigation: investigation name
        experiment: experiment name (can be None)
        logger: logging object (or None)

    Returns:
        dictionary whose keys are the experiments and values are scans
    """
    inv_path = os.path.join(path, investigation)
    if not os.path.exists(inv_path):
        raise RuntimeError(f'Investigation {investigation} does not exist')
    if experiment is not None:
        exp_path = os.path.join(inv_path, experiment)
        if not os.path.exists(inv_path):
            raise RuntimeError(f'Experiment {experiment} does not exist')
        try:
            scan_list = sorted([(int(f.name[:6]), f.name[7:]) for f in os.scandir(exp_path) if f.is_dir() and not f.name.startswith('.')])
        except ValueError:
            raise RuntimeError(f'Alien directory {exp_path}')
        return {experiment: scan_list}

    all_exp = {f.name: f.path for f in os.scandir(inv_path) if f.is_dir()}
    scan_dict = {}
    for exp, exp_path in all_exp.items():
        try:
            scan_list = sorted([(int(f.name[:6]), f.name[7:]) for f in os.scandir(exp_path) if f.is_dir() and not f.name.startswith('.')])
        except ValueError:
            if logger:
                logger.warning(f'{exp_path} is an alien directory. Ignored.')
            continue
        scan_dict[exp] = scan_list

    return scan_dict


@proxydevice(address=None)
class ManagerBase(DriverBase):
    """
    Management of experiment scan structure.

    Any package has to subclass this class with
      * the `register_driver` decorator, and
      * the `proxydevice` decorator, with the appropriate address.

    ::

        @register_driver
        @proxydevice(address=(IP, PORT))
        class Manager(ManagerBase):
            pass

    The subclass can be augmented with custom methods decorated with `proxycall`.
    """

    # Allowed characters for experiment and investigation names
    _VALID_CHAR = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-:'

    # Will be replaced by subclass
    DEFAULT_DATA_PATH = None

    DEFAULT_CONFIG = DriverBase.DEFAULT_CONFIG.copy()
    DEFAULT_CONFIG.update(
                      {'data_path':None,
                       'experiment':None,
                       'investigation':None,
                       'last_scan_info': {}},)

    def __init__(self, data_path=None):
        """
        Manager for investigations, experiments and scans.

        Args:
            data_path (str): path to data directory
        """
        super().__init__()

        if data_path is None:
            self.base_path = self.DEFAULT_DATA_PATH
        else:
            self.base_path = data_path

        # Set initial parameters
        self._running = False
        self._scan_name = None
        self._label = None
        self._base_file_name = None
        self._next_scan = None

        try:
            self._scan_number = self.next_scan()
        except Exception as e:
            self.logger.warning('Could not find first available scan number (have experiment and investigation been set?)')
        self.counter = 0

        self.scan_info = {}
        self.last_scan_info = self.config['last_scan_info']

    @proxycall()
    def get_meta(self):
        """
        Overriding default get_meta to return scan_info (empty if not in a scan)
        """
        if not self.scan_info:
            # Not currently in a scan
            return {'investigation': self.investigation,
                    'experiment': self.experiment,
                    'last_scan': self._scan_number or None}
        else:
            return self.scan_info

    @proxycall()
    def start_scan(self, label=None, localmeta=None):
        """
        Start a new scan.
        Args:
            label: an optional label to be used for directory and file naming.
            localmeta: Additional metadata to attach to the saved file(s)
        Returns:
            `scan_info` dict with scan information.
        """
        if self._running:
            raise RuntimeError(f'Scan {self.scan_name} already running')

        # New scan start time
        start_time = now()

        # Get new scan number
        self._scan_number = self.next_scan()

        # Create scan name
        today = datetime.now().strftime('%y-%m-%d')

        scan_name = f'{self._scan_number:06d}_{today}'
        if label is not None:
            scan_name += f'_{label}'

        self._scan_name = scan_name
        self._base_file_name = scan_name + '_{0:06d}'

        self._running = True
        self._label = label
        self.counter = 0

        # Store local metadata
        if localmeta is None:
            local_meta = {}

        # Create path (ok even if on control host)
        os.makedirs(os.path.join(self.base_path, self.path, scan_name), exist_ok=True)

        scan_info = {'scan_number': self._scan_number,
                'scan_name': scan_name,
                'investigation': self.investigation,
                'experiment': self.experiment,
                'path': self.path,
                'start_time': start_time}
        scan_info.update(localmeta)

        # Store for status access
        self.scan_info = scan_info

        self.logger.info(f'Starting scan {scan_name}')

        return scan_info

    @proxycall()
    def end_scan(self):
        """
        Finalize the scan
        """
        if not self._running:
            raise RuntimeError(f'No scan currently running')

        self._running = False

        self.last_scan_info = self.scan_info
        self.last_scan_info['end_time'] = now()
        self.last_scan_info['counter'] = self.counter

        self.config['last_scan_info'] = self.last_scan_info

        self.logger.info(f'Scan {self.scan_info["scan_name"]} ended.')

        self.scan_info = {}

        return self.last_scan_info

    @proxycall()
    def status(self):
        """
        Summary of current configuration
        """
        ns = self.next_scan()
        return {'investigation': self.investigation,
                'experiment': self.experiment,
                'last_scan': None if (ns is None or ns==0) else ns-1}

    @proxycall()
    def scan_status(self):
        """
        Return information about current scan if running, otherwise about the last scan
        """
        out = {}
        if self._running:
            out.update(self.scan_info)
            out['counter'] = self.counter
            out['now'] = now()
        else:
            out.update(self.last_scan_info)

        return out

    @proxycall()
    def next_prefix(self):
        """
        Return full prefix identifier and increment counter.
        """
        if not self._running:
            raise RuntimeError(f'No scan currently running')
        prefix = self._base_file_name.format(self.counter)
        self.counter += 1
        return prefix

    @proxycall()
    def get_counter(self):
        """
        Return current counter value (unlike next_prefix, does not increment the counter)
        """
        return self.counter

    @proxycall()
    def next_scan(self):
        """
        Return the next available scan number based on the analysis of the
        experiment path.
        """
        try:
            all_scans = list_scans(self.base_path, investigation=self.investigation, experiment=self.experiment, logger=self.logger)
        except RuntimeError as e:
            return None
        scans = all_scans[self.experiment]
        if not scans:
            # No scan yet in the investigation/experiment path
            return 0
        else:
            # Scans is a sorted list of tuples (scan number, scan label)
            return scans[-1][0] + 1

    @proxycall()
    def list_inv(self):
        """
        List all existing investigations.
        Returns:
            a list of strings.
        """
        return list_investigations(self.base_path)

    @proxycall()
    def list_exp(self, inv=None):
        """
        List all existing experiments in given (or current) investigation.
        Returns:
            a list of strings.
        """
        if inv is None:
            inv = self.investigation

        all_scans = list_scans(self.base_path, investigation=inv, logger=self.logger)
        return list(all_scans.keys())

    @proxycall()
    def list_scans(self, inv=None, exp=None):
        """
        List all existing experiments in given (or current) investigation and given (or current) experiment.
        Returns:
            a list of tuples (scan number, scan label)
        """
        if inv is None:
            inv = self.investigation
        if exp is None:
            exp = self.experiment

        all_scans = list_scans(self.base_path, investigation=inv, experiment=exp, logger=self.logger)
        return all_scans[exp]

    def _check_path(self):
        """
        If the current investigation / experiment values are set, check if path exists.
        """
        try:
            full_path = os.path.join(self.base_path, self.path)
            if os.path.exists(full_path):
                self.logger.info(f'Path {full_path} selected (exists).')
            else:
                os.makedirs(full_path, exist_ok=True)
                self.logger.info(f'Created path {full_path}.')
        except RuntimeError as e:
            self.logger.warning(str(e))

    def _valid_name(self, s):
        """
        Confirm that the given string can be used as part of a path
        """
        return all(c in self._VALID_CHAR for c in s)

    @proxycall()
    @property
    def scan_name(self):
        """
        Return the full scan name - none if no scan is running.
        """
        if not self._running:
            return None
        return self._scan_name

    @proxycall()
    @property
    def investigation(self):
        """
        The current investigation name.

        *** Setting the investigation makes experiment None. ***
        """
        return self.config.get('investigation')

    @investigation.setter
    def investigation(self, v):
        if v is None:
            raise RuntimeError(f'Investigation should not be set to "None"')
        if self._running:
            raise RuntimeError(f'Investigation cannot be modified while a scan is running.')
        if not self._valid_name(v):
            raise RuntimeError(f'Invalid investigation name: {v}')
        self.config['investigation'] = v
        self.config['experiment'] = None

    @proxycall()
    @property
    def experiment(self):
        """
        The current experiment name.
        """
        return self.config['experiment']

    @experiment.setter
    def experiment(self, v):
        if v is None:
            raise RuntimeError(f'Experiment should not be set to "None"')
        if self._running:
            raise RuntimeError(f'Experiment cannot be modified while a scan is running.')
        if self.investigation is None:
            raise RuntimeError(f'Investigation is not set.')
        if not self._valid_name(v):
            raise RuntimeError(f'Invalid experiment name: {v}')
        self.config['experiment'] = v
        self._check_path()

    @proxycall()
    @property
    def scanning(self):
        """
        True if a scan is currently running
        """
        return self._running

    @proxycall()
    @property
    def base_path(self):
        """
        Return base data path.
        """
        return self.config['data_path']

    @base_path.setter
    def base_path(self, v):
        self.config['data_path'] = v

    @property
    def path(self):
        """
        Return experiment path
        """
        experiment = self.experiment
        investigation = self.investigation
        if (experiment is None) or (investigation is None):
            raise RuntimeError('Experiment or Investigation not set.')
        return os.path.join(investigation, experiment)

    @proxycall()
    @property
    def scan_path(self):
        """
        Return scan path - None if no scan is running.
        """
        if not self._running:
            return None
        return os.path.join(self.path, self.scan_name)

    @proxycall()
    @property
    def scan_number(self):
        """
        Return scan name - None if no scan is running.
        """
        if not self._running:
            return None
        return self._scan_number

    @proxycall()
    @property
    def investigations(self):
        """
        Return full investigation tree.
        """
        return self.list_inv()
