document.addEventListener("DOMContentLoaded", () => {
    const tableBody = document.querySelector("#requests-table tbody");
    const errorContainer = document.getElementById("error-container");

    const fetchRequests = async () => {
        try {
            const response = await fetch("/api/requests");
            
            if (response.status === 503) {
                const data = await response.json();
                showError(data.detail || "Gateway non disponibile");
                return;
            }
            
            if (!response.ok) {
                showError("Errore durante il recupero dei dati");
                return;
            }

            const data = await response.json();
            clearError();
            updateTable(data.events);
        } catch (error) {
            console.error("Fetch error:", error);
            showError("Errore di connessione al backend UI");
        }
    };

    const showError = (message) => {
        // Only show if it's different to avoid flashing
        if (!errorContainer.innerHTML.includes(message)) {
            errorContainer.innerHTML = `<div class="error">${message}</div>`;
        }
    };

    const clearError = () => {
        errorContainer.innerHTML = "";
    };

    const updateTable = (events) => {
        if (!events || events.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4">No requests found.</td></tr>';
            return;
        }

        // Aggregate events by requestId to get current status
        const requests = {};
        
        events.forEach(event => {
            if (!event.args || event.args.requestId == null) return;
            
            const reqId = event.args.requestId;
            if (!requests[reqId]) {
                requests[reqId] = {
                    requestId: reqId,
                    deviceId: event.args.deviceId || "N/A",
                    owner: event.args.owner || "N/A",
                    status: "Unknown"
                };
            }
            
            // Update fields if they are present in later events
            if (event.args.deviceId) requests[reqId].deviceId = event.args.deviceId;
            if (event.args.owner) requests[reqId].owner = event.args.owner;
            
            // Determine status based on event type
            if (event.event === "OnboardingRequested") requests[reqId].status = "Pending";
            else if (event.event === "OnboardingApproved") requests[reqId].status = "Approved";
            else if (event.event === "OnboardingRejected") requests[reqId].status = "Rejected";
            else if (event.event === "OnboardingRevoked") requests[reqId].status = "Revoked";
        });

        tableBody.innerHTML = "";
        
        Object.values(requests).forEach(req => {
            const tr = document.createElement("tr");
            
            const tdStatus = document.createElement("td");
            tdStatus.textContent = req.status;
            
            const tdDevice = document.createElement("td");
            tdDevice.textContent = req.deviceId;
            
            const tdOwner = document.createElement("td");
            tdOwner.textContent = req.owner;
            
            const tdRequestId = document.createElement("td");
            tdRequestId.textContent = req.requestId;
            
            tr.appendChild(tdStatus);
            tr.appendChild(tdDevice);
            tr.appendChild(tdOwner);
            tr.appendChild(tdRequestId);
            
            tableBody.appendChild(tr);
        });
    };

    // Poll every 5 seconds
    setInterval(fetchRequests, 5000);
});
