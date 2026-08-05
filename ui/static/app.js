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

        // To avoid unneeded DOM updates, we can just rebuild it for now since it's simple
        tableBody.innerHTML = "";
        events.forEach(event => {
            const tr = document.createElement("tr");
            
            const tdEvent = document.createElement("td");
            tdEvent.textContent = event.event || "N/A";
            
            const tdDevice = document.createElement("td");
            tdDevice.textContent = (event.args && event.args.deviceId) ? event.args.deviceId : "N/A";
            
            const tdOwner = document.createElement("td");
            tdOwner.textContent = (event.args && event.args.owner) ? event.args.owner : "N/A";
            
            const tdRequestId = document.createElement("td");
            tdRequestId.textContent = (event.args && event.args.requestId !== undefined) ? event.args.requestId : "N/A";
            
            tr.appendChild(tdEvent);
            tr.appendChild(tdDevice);
            tr.appendChild(tdOwner);
            tr.appendChild(tdRequestId);
            
            tableBody.appendChild(tr);
        });
    };

    // Poll every 5 seconds
    setInterval(fetchRequests, 5000);
});
