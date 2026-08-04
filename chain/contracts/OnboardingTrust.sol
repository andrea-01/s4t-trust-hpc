// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/**
 * @title OnboardingTrust
 * @dev Registry of authorization for IoT devices onboarding.
 */
contract OnboardingTrust {
    enum Status { Pending, Approved, Rejected, Revoked }

    struct Request {
        string deviceId;
        address requester;
        address owner;
        Status status;
    }

    /// @notice Mapping from requestId to Request details
    mapping(uint256 => Request) public requests;

    /// @notice The ID of the next onboarding request to be created
    uint256 public nextRequestId;

    event OnboardingRequested(uint256 indexed requestId, string deviceId, address indexed requester, address indexed owner);
    event OnboardingApproved(uint256 indexed requestId, string deviceId, address indexed owner);
    event OnboardingRejected(uint256 indexed requestId, string deviceId, address indexed owner);
    event OnboardingRevoked(uint256 indexed requestId, string deviceId, address indexed revoker);

    /**
     * @dev Create a new onboarding request.
     * @param deviceId Identifier of the device.
     * @param owner Address that will own the device and must approve the request.
     */
    function requestOnboarding(string calldata deviceId, address owner) external returns (uint256) {
        uint256 requestId = nextRequestId++;
        
        requests[requestId] = Request({
            deviceId: deviceId,
            requester: msg.sender,
            owner: owner,
            status: Status.Pending
        });

        emit OnboardingRequested(requestId, deviceId, msg.sender, owner);
        return requestId;
    }

    /**
     * @dev Approve a pending request. Only the specified owner can approve.
     * @param requestId ID of the request.
     */
    function approve(uint256 requestId) external {
        Request storage req = requests[requestId];
        require(req.owner == msg.sender, "Not the owner");
        require(req.status == Status.Pending, "Request not pending");

        req.status = Status.Approved;
        emit OnboardingApproved(requestId, req.deviceId, msg.sender);
    }

    /**
     * @dev Reject a pending request. Only the specified owner can reject.
     * @param requestId ID of the request.
     */
    function reject(uint256 requestId) external {
        Request storage req = requests[requestId];
        require(req.owner == msg.sender, "Not the owner");
        require(req.status == Status.Pending, "Request not pending");

        req.status = Status.Rejected;
        emit OnboardingRejected(requestId, req.deviceId, msg.sender);
    }

    /**
     * @dev Revoke an approved request. Can be called by owner or the original requester (admin).
     * @param requestId ID of the request.
     */
    function revoke(uint256 requestId) external {
        Request storage req = requests[requestId];
        require(req.owner == msg.sender || req.requester == msg.sender, "Not authorized");
        require(req.status == Status.Approved, "Request not approved");

        req.status = Status.Revoked;
        emit OnboardingRevoked(requestId, req.deviceId, msg.sender);
    }
}
