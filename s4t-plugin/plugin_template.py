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
        self.operation = self.params.get('operation', 'INCREMENT_COUNTER') if self.params else 'INCREMENT_COUNTER'
        self.input_value = self.params.get('input_value', 10) if self.params else 10
        self.batch_size = int(self.params.get('batch_size', 0)) if self.params and 'batch_size' in self.params else 0
        self.num_threads = int(self.params.get('num_threads', 1)) if self.params and 'num_threads' in self.params else 1
        self.seed = int(self.params.get('seed', 42)) if self.params and 'seed' in self.params else 42

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
            
        stubs_dir = "/tmp/pipeline_stubs"
        os.makedirs(stubs_dir, exist_ok=True)
        import zipfile
        import io
        zip_data = base64.b64decode(STUBS_ZIP_BASE64)
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            zf.extractall(stubs_dir)
        
        if stubs_dir not in sys.path:
            sys.path.insert(0, stubs_dir)
            
    def run(self):
        try:
            LOG.info("Starting S4T plugin execution (gRPC Client)")
            
            # 1. Install dependencies
            self._ensure_grpc_installed()
            
            # 2. Mount stubs
            self._mount_stubs()
            
            # 3. Import gRPC modules (safe now that zip is extracted and in sys.path)
            import grpc
            import pipeline_pb2
            import pipeline_pb2_grpc
            
            # 4. Execute gRPC call
            channel = grpc.insecure_channel(self.worker_addr)
            stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
            
            op_str = str(self.operation).upper()
            if op_str in ("VERIFY_SIGNATURES_BATCH", "2"):
                LOG.info(f"Connecting to worker at {self.worker_addr} for VERIFY_SIGNATURES_BATCH (batch={self.batch_size}, threads={self.num_threads}, seed={self.seed})")
                req = pipeline_pb2.TaskRequest(
                    operation=pipeline_pb2.OperationType.VERIFY_SIGNATURES_BATCH,
                    batch_size=self.batch_size,
                    num_threads=self.num_threads,
                    seed=self.seed,
                    pipeline_id=self.uuid
                )
                response = stub.ExecuteTask(req)
                LOG.info(f"Worker {response.node_id} verified {response.valid_count}/{self.batch_size} signatures in {response.time_seconds:.6f}s")
                self.q_result.put(f"SUCCESS: Worker {response.node_id} verified {response.valid_count}/{self.batch_size} signatures in {response.time_seconds:.6f}s throughput={response.throughput:.2f}")
            else:
                LOG.info(f"Connecting to worker at {self.worker_addr} with input_value {self.input_value}")
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
