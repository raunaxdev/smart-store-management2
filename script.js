const API_BASE_URL = "https://smart-store-management.onrender.com/api";
let forecastChartInstance = null;
let rawInventoryData = [];

function formatTitleCase(str) {
    if (!str) return "";
    return str.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-emerald-600' : type === 'error' ? 'bg-rose-600' : 'bg-indigo-600';
    
    toast.className = `${bgColor} text-white px-4 py-3 rounded-lg shadow-lg text-sm flex items-center gap-2 transition-all duration-300 transform translate-x-full`;
    toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-xmark' : 'fa-circle-info'}"></i> <span>${message}</span>`;
    
    container.appendChild(toast);
    setTimeout(() => toast.classList.remove('translate-x-full'), 10);

    setTimeout(() => {
        toast.classList.add('translate-x-full');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

document.addEventListener("DOMContentLoaded", () => {
    loadInventoryData();
    loadKhataData();
});

async function loadInventoryData() {
    try {
        const response = await fetch(`${API_BASE_URL}/predictions`);
        if (!response.ok) throw new Error("Backend server error");
        
        const data = await response.json();
        rawInventoryData = data.inventory_forecast || [];
        
        document.getElementById("kpiTotalProducts").innerText = data.summary.total_products || 0;
        document.getElementById("kpiRevenue").innerText = "₹" + (data.summary.projected_revenue || 0).toLocaleString('en-IN');
        document.getElementById("kpiAlerts").innerText = data.summary.reorder_alerts_count || 0;

        renderTable(rawInventoryData);
        renderChart(rawInventoryData);

    } catch (error) {
        showToast("Cannot connect to Flask Server on port 5000.", "error");
    }
}

function filterInventory() {
    const query = document.getElementById("tableSearch").value.toLowerCase();
    const filtered = rawInventoryData.filter(item => 
        item.product_name.toLowerCase().includes(query) ||
        item.product_id.toLowerCase().includes(query) ||
        item.category.toLowerCase().includes(query)
    );
    renderTable(filtered);
}

function deleteItem(productId) {
    if (confirm(`Are you sure you want to remove item '${productId}' permanently from your store?`)) {
        fetch(`${API_BASE_URL}/delete-product/${productId}`, { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                showToast(data.message, "success");
                loadInventoryData();
            })
            .catch(() => showToast("Failed to delete item", "error"));
    }
}

function renderTable(inventory) {
    const tableBody = document.getElementById("inventoryTableBody");
    if (!tableBody) return;
    tableBody.innerHTML = "";

    if (!inventory || inventory.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="10" class="py-6 text-center text-slate-400">No store items found.</td></tr>`;
        return;
    }

    inventory.forEach(item => {
        const formattedName = formatTitleCase(item.product_name);
        const formattedCategory = formatTitleCase(item.category);

        let statusBadge = item.status === "CRITICAL_REORDER" 
            ? `<span class="bg-rose-500/10 text-rose-400 border border-rose-500/20 px-3 py-1 rounded-md text-xs font-semibold whitespace-nowrap">Critical Reorder</span>`
            : item.status === "REORDER_NEEDED"
            ? `<span class="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-3 py-1 rounded-md text-xs font-semibold whitespace-nowrap">Reorder Needed</span>`
            : `<span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-md text-xs font-semibold whitespace-nowrap">Stock Sufficient</span>`;

        let waBtn = "";
        if (item.status === "CRITICAL_REORDER" || item.status === "REORDER_NEEDED") {
            const waText = encodeURIComponent(`Hello Wholesaler, Urgent order requirement for Raunak's Kirana: ${formattedName} (${item.product_id}) - ${item.suggested_reorder_qty} units needed.`);
            waBtn = `<a href="https://wa.me/?text=${waText}" target="_blank" class="bg-emerald-600/20 hover:bg-emerald-600 text-emerald-400 hover:text-white border border-emerald-500/30 px-3 py-1 rounded text-xs transition flex items-center justify-center gap-1 mx-auto w-fit whitespace-nowrap"><i class="fa-brands fa-whatsapp"></i> Order</a>`;
        } else {
            waBtn = `<span class="text-slate-500 text-xs text-center block">N/A</span>`;
        }

        const deleteAction = `<button onclick="deleteItem('${item.product_id}')" class="text-rose-400 hover:text-rose-300 p-1 transition" title="Remove Item"><i class="fa-solid fa-trash-can"></i></button>`;

        const row = `
            <tr class="hover:bg-slate-800/40 transition border-b border-slate-700/30">
                <td class="py-4 px-6 font-mono text-xs text-indigo-300 font-bold">${item.product_id}</td>
                <td class="py-4 px-6 font-medium text-white">${formattedName}</td>
                <td class="py-4 px-6 text-slate-400">${formattedCategory}</td>
                <td class="py-4 px-6 text-emerald-400 font-semibold">₹${item.unit_price}</td>
                <td class="py-4 px-6 font-semibold ${item.current_stock === 0 ? 'text-rose-400 font-bold' : ''}">${item.current_stock} units</td>
                <td class="py-4 px-6 text-indigo-300 font-medium">${item.predicted_demand_30d} units</td>
                <td class="py-4 px-6 text-rose-400 font-medium">${item.suggested_reorder_qty} units</td>
                <td class="py-4 px-6 text-center">${statusBadge}</td>
                <td class="py-4 px-6 text-center">${waBtn}</td>
                <td class="py-4 px-6 text-center">${deleteAction}</td>
            </tr>
        `;
        tableBody.innerHTML += row;
    });
}

function renderChart(inventory) {
    const chartCanvas = document.getElementById('forecastChart');
    if (!chartCanvas) return;
    const ctx = chartCanvas.getContext('2d');

    if (forecastChartInstance) forecastChartInstance.destroy();

    forecastChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: inventory.map(item => formatTitleCase(item.product_name)),
            datasets: [
                { 
                    label: 'Current Stock', 
                    data: inventory.map(item => item.current_stock), 
                    backgroundColor: '#6366f1', 
                    borderRadius: 6 
                },
                { 
                    label: 'Predicted Demand (30D)', 
                    data: inventory.map(item => item.predicted_demand_30d), 
                    backgroundColor: '#10b981', 
                    borderRadius: 6 
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { 
                    position: 'top',
                    labels: { color: '#94a3b8', font: { family: 'sans-serif', size: 12 } } 
                } 
            },
            scales: { 
                x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } }, 
                y: { beginAtZero: true, min: 0, ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } } 
            }
        }
    });
}

async function submitNewProduct(event) {
    event.preventDefault();
    const payload = {
        product_id: document.getElementById("newProdId").value.trim(),
        product_name: document.getElementById("newProdName").value.trim(),
        category: document.getElementById("newCategory").value.trim(),
        unit_price: document.getElementById("newPrice").value,
        current_stock: document.getElementById("newStock").value,
        reorder_threshold: document.getElementById("newThreshold").value
    };

    try {
        const response = await fetch(`${API_BASE_URL}/add-product`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const resData = await response.json();
        if (response.ok) {
            showToast(resData.message, "success");
            document.getElementById("addProductModal").classList.add("hidden");
            document.getElementById("addProductForm").reset();
            loadInventoryData();
        } else {
            showToast(resData.error || "Error adding product", "error");
        }
    } catch (err) {
        showToast("Server communication error!", "error");
    }
}

async function submitSale(event) {
    event.preventDefault();
    const productId = document.getElementById("posProductId").value.trim();
    const quantity = document.getElementById("posQty").value;

    try {
        const response = await fetch(`${API_BASE_URL}/record-sale`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product_id: productId, quantity_sold: quantity })
        });
        const resData = await response.json();
        if (response.ok) {
            showToast("Sale recorded!", "success");
            document.getElementById("posModal").classList.add("hidden");
            document.getElementById("posForm").reset();

            document.getElementById("receiptDate").innerText = new Date().toLocaleString('en-IN');
            document.getElementById("receiptItemName").innerText = formatTitleCase(resData.product_name);
            document.getElementById("receiptRate").innerText = `₹${resData.unit_price} x ${resData.quantity_sold}`;
            document.getElementById("receiptTotal").innerText = `₹${resData.total_bill}`;
            document.getElementById("receiptModal").classList.remove("hidden");

            loadInventoryData();
        } else {
            showToast(resData.error || "Sale failed", "error");
        }
    } catch (err) {
        showToast("Server communication error!", "error");
    }
}

// Udhaar Khata Handlers
async function openKhataModal() {
    document.getElementById("khataModal").classList.remove("hidden");
    loadKhataData();
}

async function loadKhataData() {
    try {
        const res = await fetch(`${API_BASE_URL}/khata`);
        const data = await res.json();
        
        document.getElementById("kpiUdhaar").innerText = "₹" + (data.total_pending || 0).toLocaleString('en-IN');
        
        const listContainer = document.getElementById("khataList");
        listContainer.innerHTML = "";
        
        if (!data.records || data.records.length === 0) {
            listContainer.innerHTML = `<p class="text-slate-500 italic">No udhaar records found.</p>`;
            return;
        }

        data.records.forEach(r => {
            listContainer.innerHTML += `
                <div class="bg-slate-900 p-2.5 rounded border border-slate-700/60 flex justify-between items-center">
                    <div>
                        <p class="font-semibold text-white">${formatTitleCase(r.name)} <span class="text-slate-400 font-normal">(${r.phone || 'No phone'})</span></p>
                        <p class="text-slate-400 text-[10px]">${r.note || 'General Purchase'}</p>
                    </div>
                    <span class="text-amber-400 font-bold">₹${r.amount}</span>
                </div>
            `;
        });
    } catch (err) {
        console.error("Khata error:", err);
    }
}

async function submitKhata(event) {
    event.preventDefault();
    const payload = {
        name: document.getElementById("khataName").value.trim(),
        phone: document.getElementById("khataPhone").value.trim(),
        amount: document.getElementById("khataAmount").value,
        note: document.getElementById("khataNote").value.trim()
    };

    try {
        const res = await fetch(`${API_BASE_URL}/khata/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            showToast("Failed to add khata entry", "error");
            return;
        }

        const data = await res.json();
        showToast(data.message, "success");
        document.getElementById("khataForm").reset();
        loadKhataData();

    } catch (err) {
        showToast("Server connection error!", "error");
    }
}