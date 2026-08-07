#pragma once

#include <string>
#include <vector>
#include <memory>
#include <openssl/evp.h>

struct EVP_PKEY_Deleter {
    void operator()(EVP_PKEY* p) const {
        if (p) EVP_PKEY_free(p);
    }
};

using EVP_PKEY_ptr = std::unique_ptr<EVP_PKEY, EVP_PKEY_Deleter>;

struct EVP_MD_CTX_Deleter {
    void operator()(EVP_MD_CTX* p) const {
        if (p) EVP_MD_CTX_free(p);
    }
};

using EVP_MD_CTX_ptr = std::unique_ptr<EVP_MD_CTX, EVP_MD_CTX_Deleter>;

struct Device {
    std::string device_id;
    EVP_PKEY_ptr keypair;
    std::vector<uint8_t> message;
    std::vector<uint8_t> signature;
};

class DeviceGenerator {
public:
    // Generates a list of synthetic devices with their keypair and a valid signature over the message.
    // seed is used to ensure deterministic device_id and message generation.
    static std::vector<Device> generate_devices(size_t count, unsigned int seed = 42);
};
