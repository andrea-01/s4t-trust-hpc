#include "device_generator.hpp"
#include <openssl/core_names.h>
#include <openssl/err.h>
#include <random>
#include <stdexcept>
#include <iostream>

struct EVP_MD_CTX_Deleter {
    void operator()(EVP_MD_CTX* p) const { if (p) EVP_MD_CTX_free(p); }
};
using EVP_MD_CTX_ptr = std::unique_ptr<EVP_MD_CTX, EVP_MD_CTX_Deleter>;


std::vector<Device> DeviceGenerator::generate_devices(size_t count, unsigned int seed) {
    std::vector<Device> devices;
    devices.reserve(count);

    std::mt19937 gen(seed);
    std::uniform_int_distribution<> byte_dist(0, 255);

    for (size_t i = 0; i < count; ++i) {
        Device dev;
        dev.device_id = "device_" + std::to_string(i);

        // Generate message
        dev.message.resize(32);
        for (auto& b : dev.message) {
            b = static_cast<uint8_t>(byte_dist(gen));
        }

        // Generate keypair using OpenSSL 3.x simplified key generation
        EVP_PKEY* raw_pkey = EVP_PKEY_Q_keygen(nullptr, nullptr, "EC", "P-256");
        if (!raw_pkey) {
            throw std::runtime_error("Failed to generate EVP_PKEY");
        }
        dev.keypair.reset(raw_pkey);

        // Sign the message
        EVP_MD_CTX_ptr mdctx(EVP_MD_CTX_new());
        if (!mdctx) {
            throw std::runtime_error("Failed to create EVP_MD_CTX");
        }

        if (EVP_DigestSignInit(mdctx.get(), nullptr, EVP_sha256(), nullptr, dev.keypair.get()) <= 0) {
            throw std::runtime_error("Failed to init DigestSign");
        }

        size_t siglen = 0;
        if (EVP_DigestSign(mdctx.get(), nullptr, &siglen, dev.message.data(), dev.message.size()) <= 0) {
            throw std::runtime_error("Failed to determine signature length");
        }

        dev.signature.resize(siglen);
        if (EVP_DigestSign(mdctx.get(), dev.signature.data(), &siglen, dev.message.data(), dev.message.size()) <= 0) {
            throw std::runtime_error("Failed to sign message");
        }
        dev.signature.resize(siglen); // Adjust to actual length

        devices.push_back(std::move(dev));
    }

    return devices;
}
