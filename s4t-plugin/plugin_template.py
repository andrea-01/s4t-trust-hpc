import sys
import os
import subprocess
import base64
import logging

from iotronic_lightningrod.modules.plugins.Plugin import Plugin

LOG = logging.getLogger(__name__)

# The build script will replace this with actual base64
STUBS_ZIP_BASE64 = "###STUBS_ZIP_BASE64###"

class Worker(Plugin):
    def __init__(self, uuid, name, q_result, params=None):
        super(Worker, self).__init__(uuid, name, q_result, params)
        self.worker_addr = self.params.get('worker_addr', 'deploy-worker-1-1:50051') if self.params else 'deploy-worker-1-1:50051'
        self.input_value = self.params.get('input_value', 10) if self.params else 10

    def _ensure_grpc_installed(self):
        try:
            import grpc
            import google.protobuf
            LOG.info("grpcio and protobuf are already installed")
        except ImportError:
            LOG.info("grpcio or protobuf not found, installing dynamically...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "grpcio", "protobuf"])
            LOG.info("dependencies installed successfully")
            
    def _mount_stubs(self):
        if STUBS_ZIP_BASE64.startswith("###"):
            LOG.warning("Stubs zip not injected, assuming local development mode")
            # If running locally, maybe stubs are in sys.path already
            return
            
        zip_path = "/tmp/pipeline_stubs.zip"
        if not os.path.exists(zip_path):
            with open(zip_path, "wb") as f:
                f.write(base64.b64decode(STUBS_ZIP_BASE64))
        
        if zip_path not in sys.path:
            sys.path.insert(0, zip_path)
            
    def run(self):
        try:
            LOG.info("Starting S4T plugin execution (gRPC Client)")
            
            # 1. Install dependencies
            self._ensure_grpc_installed()
            
            # 2. Mount stubs
            self._mount_stubs()
            
            # 3. Import gRPC modules (safe now that zip is in sys.path and grpc is installed)
            import grpc
            import pipeline_pb2
            import pipeline_pb2_grpc
            
            # 4. Execute gRPC call
            LOG.info(f"Connecting to worker at {self.worker_addr} with input_value {self.input_value}")
            channel = grpc.insecure_channel(self.worker_addr)
            stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
            
            # operation=1 is INCREMENT_COUNTER
            req = pipeline_pb2.TaskRequest(
                operation=pipeline_pb2.OperationType.INCREMENT_COUNTER,
                input_value=int(self.input_value),
                pipeline_id=self.uuid
            )
            
            response = stub.ExecuteTask(req)
            LOG.info(f"Worker {response.node_id} returned: {response.output_value}")
            
            self.q_result.put(f"SUCCESS: Worker {response.node_id} incremented {self.input_value} -> {response.output_value}")
            
        except Exception as e:
            LOG.error(f"Plugin execution failed: {str(e)}")
            self.q_result.put(f"ERROR: {str(e)}")
