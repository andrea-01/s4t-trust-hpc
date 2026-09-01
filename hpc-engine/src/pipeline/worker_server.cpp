#include "worker_server.hpp"
#include "device_generator.hpp"
#include "signature_bench.hpp"
#include <iostream>
#include <chrono>

PipelineWorkerServiceImpl::PipelineWorkerServiceImpl(const std::string& node_id)
    : node_id_(node_id) {}

grpc::Status PipelineWorkerServiceImpl::Ping(grpc::ServerContext* /*context*/, const google::protobuf::Empty* /*request*/, pipeline::Status* response) {
    response->set_healthy(true);
    response->set_node_id(node_id_);
    return grpc::Status::OK;
}

grpc::Status PipelineWorkerServiceImpl::ExecuteTask(grpc::ServerContext* /*context*/, const pipeline::TaskRequest* request, pipeline::TaskResult* response) {
    if (request->operation() == pipeline::INCREMENT_COUNTER) {
        std::cout << "[" << node_id_ << "] Executing INCREMENT_COUNTER for pipeline " << request->pipeline_id() << "\n";
        response->set_output_value(request->input_value() + 1);
        response->set_node_id(node_id_);
        
        auto now = std::chrono::system_clock::now();
        std::time_t now_c = std::chrono::system_clock::to_time_t(now);
        char buf[100];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&now_c));
        response->set_timestamp(buf);
        
        return grpc::Status::OK;
    }

    if (request->operation() == pipeline::VERIFY_SIGNATURES_BATCH) {
        std::cout << "[" << node_id_ << "] Executing VERIFY_SIGNATURES_BATCH (batch_size=" 
                  << request->batch_size() << ", threads=" << request->num_threads() 
                  << ", seed=" << request->seed() << ") for pipeline " 
                  << request->pipeline_id() << "\n";

        size_t batch_size = request->batch_size();
        unsigned int seed = request->seed();
        int num_threads = request->num_threads() > 0 ? request->num_threads() : 1;

        auto devices = DeviceGenerator::generate_devices(batch_size, seed);
        BenchResult bench_res = SignatureBench::run_parallel(devices, num_threads, batch_size);

        response->set_node_id(node_id_);
        response->set_time_seconds(bench_res.time_seconds);
        response->set_throughput(bench_res.throughput);
        response->set_valid_count(static_cast<uint32_t>(bench_res.valid_count));

        auto now = std::chrono::system_clock::now();
        std::time_t now_c = std::chrono::system_clock::to_time_t(now);
        char buf[100];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&now_c));
        response->set_timestamp(buf);

        return grpc::Status::OK;
    }
    
    // Explicitly handle unknown operations as requested by the user
    return grpc::Status(grpc::StatusCode::UNIMPLEMENTED, "Operation not recognized or unimplemented");
}

void RunServer(const std::string& address, const std::string& node_id) {
    PipelineWorkerServiceImpl service(node_id);
    grpc::ServerBuilder builder;
    builder.AddListeningPort(address, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
    std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
    std::cout << "Worker " << node_id << " listening on " << address << std::endl;
    server->Wait();
}
