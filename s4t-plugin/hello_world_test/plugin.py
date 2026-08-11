from iotronic_lightningrod.modules.plugins import Plugin
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

class Worker(Plugin.Plugin):
    def __init__(self, uuid, name, q_result, params=None):
        super(Worker, self).__init__(uuid, name, q_result, params)

    def run(self):
        LOG.info("Hello World Plugin Executed")
        message = self.params.get("message", "Hello from S4T Plugin!") if self.params else "Hello from S4T Plugin!"
        self.q_result.put(f"SUCCESS: {message}")
