import sys
import os
import subprocess
import base64
import logging

from iotronic_lightningrod.modules.plugins.Plugin import Plugin

LOG = logging.getLogger(__name__)

# The build script will replace this with actual base64
STUBS_ZIP_BASE64 = "UEsDBBQAAAAIAOJrDF2mXnbLRQMAAGEIAAAPABwAcGlwZWxpbmVfcGIyLnB5VVQJAAN3WXxqd1l8anV4CwABBOgDAAAE6AMAAJVVXW+bPBS+z6/wsotk1cogJE0XqdKyhk1RN2BAVk1vXlkQnBQNMLPNlOxiv33HfIRCoy67SMD283F8fI55iS4vLtGGhlG6m6FcbC+v5UzvJfpIUsJ8QUIUHJB4IChjVNANjVGQb7eEASnJopgwBaGFhUzLQ8Zi6b0AKqc525AZyqKMxFFKlIIKC7Z8Ah3ZB/FAU/SVMB7RdIYmyuhK0Xr9fr+xfeoXEgUQvS2jCdpRuosrZakYJRllAoWEb1iUCcqQzxFuhmeycEbBsU0t5p7l80MS0BiHvvADn5OC35k7yVeiVBCW+nEtFORRHJIy9uod0vbuXZkLHKWcMAEZg5CAOixZ/FWvJ+1wGKCbJ8bKgmz9PBZDQD27CZJk4oCzYCTdSwwOqcA1rhiUIIkCtYXh3jpL27Mc6dtJWOOrzMPQJSzy4+gXCT9AzQyDwTpd71XSrpD1XhvB7HU9C2MffkEZzJs6kDdFEBWlf1EoXbnCFzmvFLbF3PSB+LF4OMDkNQw1JP+G0qANS6GwcBRWsFEFE+v+plgPPJ9/d8iPnHAhidJQ0ExWKZzEE3GIWgdxbaocN2fVYO+QkdJb00vtKM1ygX/6cU46/nt10obWck2oehPqB8CkZaAckl4xxwVzQ3PRddG6Ln9LRimoyb2LKIFU+EnWDePiBpbZqd1OpLimWbbhzL2lZeKVeWda9yZMqkBW27CleesYnw3Tw7fWyvQMp4JpMrW/y8qxq2zcU/adsJKvq8Xa2IbLrFK8UrotZ8jiqSpLbc6oqZ9Zme71fjzZk00uiExrHWBDaFeFVBt3F+VJBLI4C3N9IPt0F9PAjzk0TPUGfVm3uvJePj8Tzv0dmaehkebJ4thVfNj022tUC3XZHs0eUUCkkmuzB8digk4ePFaLtiil4nE3K3jlGvgWN3x31oM7/zhUcEz9kISYZvLY5d5MmhLA1LL/DfDx6L1vtjH4X8H8eCNgKCYmbkbT8fkUkoY3uj5pE1xv7q3ck+KT6RlQKfr2bRvozd07x/iyMlzvpLCmaucSpPxIVU/B3dWn0/IjdXQmvlCfdtD20jY+LU3j3nLuDOekg65P/4EjXcZX+nMfpYSGOXw6+AbuyFe9P1BLAwQUAAAACADiawxdH0ixRAQFAABdFAAAFAAcAHBpcGVsaW5lX3BiMl9ncnBjLnB5VVQJAAN3WXxqd1l8anV4CwABBOgDAAAE6AMAAO1XUW/bNhB+169g0wfZmKu2QbuHYB5mOGrnIXEM2133RtDS2eEiixpJLfGC/PcdScmRFNlOlgwYhurBkKy7j7zv7j6eXpPPkIJkGmKy2BB9CWQ1nQzJZKMvRUoyKbSIREIisc54ApJkSb7iaUBOL8j4Yk7C09H8lXd0dDRMOKSasDQmCuSfaBklTClQ6ColqEykMU9XRAsHusiXb2JY8hScA49ABYjj8XUmpCYrmUXl/TWTKfoqz1tKsSYrIVYJBCUMKaxgnekNzRbHhKnChsZC09LOPjgjY1WCZzyDBLdRem6frZH3Gdmgn8NxOB3Mw1P6azidjS7GpE/898H3H4L3vrO4/99sPKAUGVBcpJR64W+TcGh8w+n0Ykqn4Vk4mIUFwsfgne/Nhj+Hp1/O0KR4SU9xMWPxS54COf7YI8fvjj/43hY1xVBUnpkAkL8++cQSBZ6n5ebEI3g5nuxOcs0Trjkmogh4yaXSWySuaCKuQVq3nfjtPp1q6D3STlXXg5sIMk1GdvlQSiFP9q82lzkGw5c7LJx3WRSBuenYv2zk/tzUMIZOMhZdsRUQnirNkgShuSJMkwKU3Fa3f9fztxjfIQpZ5Nq1w7Y/IhEbsFrFUEtytiExZJDGioi0gWMMuPixf9tOz13QsJ8kwBSQPFtJhuttRC5dOGsR5wmYBjoE2UAUksTiOq3i1WPKlelMh/pGC5GoH/p1cpqbnF8ilUUGyDVPErIAlAjA/idgMmx4um2v/AdMq+gSTGgxWaKjBEeASVB7Y+BueluEaZ5qvoavbi/2767neVZ8yKTI1Fchr0DOdL7oiMXvEOmuqyHUm3OubPRoLiJuOYlFlK9RzJg2VYJhmQcTkJMcbAZUHyNVFgNFjFDKU64p7ShIlj0SXbI0haRYpFhoKLAMZR5pIQNv+2IgV+rezFyF8wkZuAYeuuegirW9N+sFE7P/fukY5CmTG2p/OzVkc/lvy+oN6uS8NSgVXstLwh85YO+jRnOW8L9A9g9raxCa22BW+szFTEvEb4M3J4NCNKisUNPgYIaZyFXwCTVtF0y3zkh4A1GuYc7U1fOJqYA9jp/67o3f1Bm9FCEOUuWJPkDKjj5wx638d3rB1FHRBwU32BAi1XCj6w3xnNVKmAI4UKCpkbKObRlXMEN8Dr6MR+eTs/A8HKMOdVv9YtCMJ6rjnwPOPDHBs8YclQmYxSF+5d+7ScZRmcZCj+7f2wNtn/OWmUohfSOoSpBn2GFxTNvrlGpB3UzZKSZF2SuGzIIwjImuLT7FXo9xTlXY97e1jvCtwJ04Ua1IAX3o/FAdzFWubfX2Ybe55nViUOvdR8vlvl526IU0HFLKAzLTrT/6VYF7CX4qeE+gabdqPp+XimA+jps7+2vHJB6VYZfDfaPSaMOszo6/41jxe21V6zrJ1XZgOqLENralUafTWLHXNU1EXruxzEk+3mQMp32xNDOZmcSmI9PkgzMymIyC1oPh5Q+En5QxjFyU9SOi1L4aW5rJFTT+E5lZSvU7jbotjnUaSYhxD5hV1R+LFBpWOPkfMMHvAyxYCX37FdVwx+9erC/zvdDiec1w6sOhlUpg8abFwIymItctb5ASFjPN7KuK7kvQuUxdocFNhmm2bO+ZXh5N5JNmv5ca8p40yhWpPpjn9vztT/zOvO5LaWs22xPZ0JF99V8dBL61wX+nDXZP+v94pH/y4P5/aoG/AVBLAQIeAxQAAAAIAOJrDF2mXnbLRQMAAGEIAAAPABgAAAAAAAEAAACkgQAAAABwaXBlbGluZV9wYjIucHlVVAUAA3dZfGp1eAsAAQToAwAABOgDAABQSwECHgMUAAAACADiawxdH0ixRAQFAABdFAAAFAAYAAAAAAABAAAApIGOAwAAcGlwZWxpbmVfcGIyX2dycGMucHlVVAUAA3dZfGp1eAsAAQToAwAABOgDAABQSwUGAAAAAAIAAgCvAAAA4AgAAAAA"

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
