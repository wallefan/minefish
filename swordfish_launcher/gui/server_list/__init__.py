import http.client
import tkinter
from ..scrollable_frame import ScrollableFrame
import json
from abc import ABC, abstractmethod

import enum


class ServerStatus(enum.Enum):
    OFFLINE = 'Down'
    STARTING = 'Starting'   # Server is in the process of starting up.
    RUNNING = 'Up'          # Server is operating normally.
    STOPPING = 'Stopping'   # Server is in the process of kicking everyone off and shutting down.
    STOPPED = 'Idle'    # Server is offline, but is ready to come online the moment someone sends it a /start request.
    MAINTENANCE = 'Maintenance mode'  # Server admin is doing some maintenance.  Server is down and will not respond
                                      # to /start requests from anyone other than said administrator.
    MAINTENANCE_RUNNING = 'Up (Maintenance mode)'  # Server is running, with a limited whitelist.


class BaseServer(ABC):
    def __init__(self, address, port=25565):
        self._status = None
        self._modlist = None
        self.address = address
        self.port = port

    def get_status(self, force_refresh=False) -> ServerStatus:
        if force_refresh or not self._status:
            self._status = self.query_status()
        return self._status

    @abstractmethod
    def query_status(self) -> ServerStatus:
        """Query (refresh) the server status.  This makes a network request and has to wait for a reply,
        so use it sparingly.

        If possible, implementations should also make a best effort to populate self._modlist."""
        return ServerStatus.OFFLINE

    def get_modlist(self):
        return []


class ServerList(tkinter.Toplevel):
    def