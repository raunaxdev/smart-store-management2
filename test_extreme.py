import requests
import time
import random
import concurrent.futures

BASE_URL = "http://127.0.0.1:5000/api"

print("=========================================================")
print("🔥 STARTING EXTREME AUTOMATED SUITE FOR RAUNAK'S KIRANA 🔥")
print("=========================================================\n")

# 1. HEALTH CHECK TEST
def test_health():
    print("1️⃣ Testing Server Health Endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            print("   ✅ SUCCESS: Server & Neon DB Active\n")
        else:
            print(f"   ❌ FAILED: Health returned status {r.status_code}\n")
    except Exception as e:
        print(f"   ❌ CRITICAL: Server connection failed ({e})\n")

# 2. BOUNDARY & MALICIOUS PAYLOAD INJECTION TEST
def test_boundary_cases():
    print("2️⃣ Testing Boundary & Edge Cases (Invalid Inputs)...")
    bad_payloads = [
        {"product_id": "", "product_name": "Test", "unit_price": 10, "current_stock": 5}, # Empty ID
        {"product_id": "P999", "product_name": "Bad Price", "unit_price": -50, "current_stock": 10}, # Negative Price
        {"product_id": "P998", "product_name": "<script>alert('hack')</script>", "unit_price": 20, "current_stock": 10}, # XSS Script
        {"product_id": "DROP TABLE products;--", "product_name": "SQLi", "unit_price": 100, "current_stock": 10} # SQL Injection
    ]

    for idx, payload in enumerate(bad_payloads, 1):
        r = requests.post(f"{BASE_URL}/add-product", json=payload)
        res_msg = r.json().get('error', r.json().get('message')) if r.status_code != 500 else "Internal Error"
        print(f"   [Edge Case {idx}] Status: {r.status_code} | Response: {res_msg}")
    print("   ✅ Boundary Injection Test Executed\n")

# 3. HIGH SPEED CONCURRENT LOAD TEST WITH AUTO-RESTOCK
def simulate_single_sale(i):
    p_id = random.choice(["P101", "P102", "P103", "P104"])
    try:
        r = requests.post(f"{BASE_URL}/record-sale", json={"product_id": p_id, "quantity_sold": 1}, timeout=5)
        return r.status_code
    except:
        return 500

def test_concurrency_stress():
    print("3️⃣ Auto-Restocking Stock & Running Concurrent Load Test (50 Requests)...")
    
    # Pre-fill stock for P101, P102, P103, P104 to avoid Insufficient Stock errors
    for pid in ["P101", "P102", "P103", "P104"]:
        requests.post(f"{BASE_URL}/add-product", json={
            "product_id": pid,
            "product_name": f"Test Item {pid}",
            "category": "Test",
            "unit_price": 100,
            "current_stock": 1000,
            "reorder_threshold": 10
        })

    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(simulate_single_sale, range(50)))
    
    duration = time.time() - start_time
    success_count = results.count(200)
    failed_count = len(results) - success_count

    print(f"   📊 Stress Results: Total: 50 | Successful Sales: {success_count} | Failed/Rejected: {failed_count}")
    print(f"   ⚡ Execution Time: {duration:.2f} seconds ({50/duration:.2f} req/sec)\n")

# 4. PREDICTIONS & ML INTEGRITY TEST
def test_ml_integrity():
    print("4️⃣ Testing ML Forecast Engine & Summary Stats...")
    r = requests.get(f"{BASE_URL}/predictions")
    if r.status_code == 200:
        data = r.json()
        summary = data.get("summary", {})
        forecast = data.get("inventory_forecast", [])
        print(f"   ✅ Total Products Tracked: {summary.get('total_products')}")
        print(f"   ✅ Projected Revenue: ₹{summary.get('projected_revenue')}")
        print(f"   ✅ Active Re-order Alerts: {summary.get('reorder_alerts_count')}")
        print(f"   ✅ Forecast Items Analyzed: {len(forecast)}\n")
    else:
        print("   ❌ ML Engine Failed!\n")

if __name__ == "__main__":
    test_health()
    test_boundary_cases()
    test_concurrency_stress()
    test_ml_integrity()
    print("=========================================================")
    print("🎉 EXTREME AUTOMATED SUITE COMPLETED!")
    print("=========================================================")