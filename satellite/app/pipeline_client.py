import grpc
import pipeline_pb2
import pipeline_pb2_grpc
from typing import List, Dict, Any

async def run_pipeline_task(pipeline_id: str, nodes: List[str], initial_value: int) -> Dict[str, Any]:
    current_value = initial_value
    trace = []
    
    for node in nodes:
        # Create an async channel to the worker
        async with grpc.aio.insecure_channel(node) as channel:
            stub = pipeline_pb2_grpc.PipelineWorkerStub(channel)
            request = pipeline_pb2.TaskRequest(
                operation=pipeline_pb2.INCREMENT_COUNTER,
                input_value=current_value,
                pipeline_id=pipeline_id
            )
            try:
                # Call ExecuteTask
                response = await stub.ExecuteTask(request)
                current_value = response.output_value
                trace.append({
                    "node_id": response.node_id,
                    "timestamp": response.timestamp,
                    "output": current_value
                })
            except grpc.RpcError as e:
                # E.g. UNIMPLEMENTED or node unreachable
                raise Exception(f"gRPC call failed on node {node}: {e.details()}")
                
    return {
        "final_value": current_value,
        "trace": trace
    }
