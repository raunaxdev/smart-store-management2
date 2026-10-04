from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from waitress import serve
import re

app = Flask(__name__)

# Full CORS Support for REST Endpoints
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type"]}})

# Neon Cloud PostgreSQL Connection String
NEON_DB_URI = "postgresql://neondb_owner:npg_3BwUa1ipFNTK@ep-bitter-sound-b502jrm0-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Create Database Connection Pool (Min 1, Max 20 connections)
db_pool = None
try:
    db_pool = SimpleConnectionPool(1, 20, dsn=NEON_DB_URI, cursor_factory=RealDictCursor)
    print("PostgreSQL Connection Pool Created Successfully!")
except Exception as e:
    print(f"Error creating connection pool: {e}")

def get_db_connection():
    if db_pool:
        return db_pool.getconn()
    return psycopg2.connect(NEON_DB_URI, cursor_factory=RealDictCursor)

def release_db_connection(conn):
    if db_pool and conn:
        db_pool.putconn(conn)
    elif conn:
        conn.close()

def sanitize_string(text):
    if not text:
        return ""
    clean = re.sub(r'<[^>]*>', '', str(text))
    clean = re.sub(r'[;\']', '', clean)
    return clean.strip()

# ------------------------------------
# ML DEMAND FORECAST ENGINE
# ------------------------------------
def run_ml_forecast():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM products ORDER BY product_id;")
        products = cur.fetchall()

        cur.execute("SELECT product_id, quantity_sold, sale_date FROM sales_logs;")
        sales = cur.fetchall()

        cur.close()

        if not products:
            return []

        df_sales = pd.DataFrame(sales) if sales else pd.DataFrame(columns=['product_id', 'quantity_sold', 'sale_date'])
        forecast_results = []

        for p in products:
            p_id = p['product_id']
            p_sales = df_sales[df_sales['product_id'] == p_id] if not df_sales.empty else pd.DataFrame()

            if len(p_sales) >= 2:
                p_sales['sale_date'] = pd.to_datetime(p_sales['sale_date'])
                p_sales = p_sales.sort_values('sale_date')
                p_sales['day_index'] = (p_sales['sale_date'] - p_sales['sale_date'].min()).dt.days

                X = p_sales[['day_index']].values
                y = p_sales['quantity_sold'].values

                model = LinearRegression()
                model.fit(X, y)

                last_day = p_sales['day_index'].max()
                future_days = np.array([[last_day + i] for i in range(1, 31)])
                predicted_daily = model.predict(future_days)
                predicted_30d = max(int(np.sum(predicted_daily)), 5)
            else:
                predicted_30d = int(p['reorder_threshold']) * 2

            current_stock = int(p['current_stock'])
            deficit = predicted_30d - current_stock

            if current_stock <= (0.3 * predicted_30d):
                status = "CRITICAL_REORDER"
            elif current_stock < predicted_30d:
                status = "REORDER_NEEDED"
            else:
                status = "STOCK_SUFFICIENT"

            forecast_results.append({
                "product_id": str(p['product_id']),
                "product_name": str(p['product_name']),
                "category": str(p['category']),
                "unit_price": float(p['unit_price']),
                "current_stock": current_stock,
                "predicted_demand_30d": predicted_30d,
                "suggested_reorder_qty": max(deficit, 0),
                "projected_revenue": round(predicted_30d * float(p['unit_price']), 2),
                "status": status
            })

        return forecast_results
    finally:
        if conn:
            release_db_connection(conn)

# ------------------------------------
# REST API ROUTES
# ------------------------------------
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "active", "database": "Neon PostgreSQL Connected"}), 200

@app.route('/api/predictions', methods=['GET'])
def get_predictions():
    try:
        results = run_ml_forecast()
        total_rev = sum(item['projected_revenue'] for item in results)
        alerts_count = sum(1 for item in results if item['status'] in ['CRITICAL_REORDER', 'REORDER_NEEDED'])

        return jsonify({
            "summary": {
                "total_products": len(results),
                "projected_revenue": total_rev,
                "reorder_alerts_count": alerts_count
            },
            "inventory_forecast": results
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/add-product', methods=['POST', 'OPTIONS'])
def add_product():
    if request.method == 'OPTIONS':
        return jsonify({"status": "OK"}), 200
    conn = None
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON payload received!"}), 400

        p_id = sanitize_string(data.get('product_id', '')).upper()
        p_name = sanitize_string(data.get('product_name', ''))
        category = sanitize_string(data.get('category', 'General'))
        
        if not p_id or not p_name:
            return jsonify({"error": "Product ID and Name are required!"}), 400

        try:
            price = float(data.get('unit_price', 0))
            stock = int(data.get('current_stock', 0))
            threshold = int(data.get('reorder_threshold', 10))
        except ValueError:
            return jsonify({"error": "Numeric format error for price or stock"}), 400

        if price <= 0:
            return jsonify({"error": "Unit price must be greater than zero!"}), 400
        if stock < 0:
            return jsonify({"error": "Stock quantity cannot be negative!"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO products (product_id, product_name, category, unit_price, current_stock, reorder_threshold)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
            product_name = EXCLUDED.product_name,
            category = EXCLUDED.category,
            unit_price = EXCLUDED.unit_price,
            current_stock = EXCLUDED.current_stock,
            reorder_threshold = EXCLUDED.reorder_threshold;
        """, (p_id, p_name, category, price, stock, threshold))

        conn.commit()
        cur.close()

        return jsonify({"message": f"Product '{p_name}' ({p_id}) saved in Neon DB!"}), 200

    except Exception as e:
        return jsonify({"error": f"DB Error: {str(e)}"}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/delete-product/<product_id>', methods=['DELETE', 'OPTIONS'])
def delete_product(product_id):
    if request.method == 'OPTIONS':
        return jsonify({"status": "OK"}), 200
    conn = None
    try:
        p_id = sanitize_string(product_id).upper()
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM products WHERE UPPER(product_id) = UPPER(%s);", (p_id,))
        cur.execute("DELETE FROM sales_logs WHERE UPPER(product_id) = UPPER(%s);", (p_id,))
        
        conn.commit()
        cur.close()

        return jsonify({"message": f"Product '{p_id}' removed from store database!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/record-sale', methods=['POST', 'OPTIONS'])
def record_sale():
    if request.method == 'OPTIONS':
        return jsonify({"status": "OK"}), 200
    conn = None
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid request payload"}), 400

        p_id = sanitize_string(data.get('product_id', '')).upper()
        try:
            qty = int(data.get('quantity_sold', 0))
            if qty <= 0:
                return jsonify({"error": "Quantity must be greater than zero"}), 400
        except ValueError:
            return jsonify({"error": "Invalid quantity number"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT product_name, unit_price, current_stock FROM products WHERE UPPER(product_id) = UPPER(%s);", (p_id,))
        prod = cur.fetchone()

        if not prod:
            cur.close()
            return jsonify({"error": f"Product ID '{p_id}' not found!"}), 404

        current_stock = prod['current_stock']
        if current_stock < qty:
            cur.close()
            return jsonify({"error": f"Insufficient stock! Available: {current_stock} units"}), 400

        new_stock = current_stock - qty
        unit_price = float(prod['unit_price'])
        total_bill = round(unit_price * qty, 2)

        cur.execute("UPDATE products SET current_stock = %s WHERE UPPER(product_id) = UPPER(%s);", (new_stock, p_id))
        cur.execute("INSERT INTO sales_logs (product_id, quantity_sold) VALUES (%s, %s);", (p_id, qty))

        conn.commit()
        cur.close()

        return jsonify({
            "message": "Sale recorded!",
            "product_id": p_id,
            "product_name": prod['product_name'],
            "unit_price": unit_price,
            "quantity_sold": qty,
            "total_bill": total_bill,
            "new_stock": new_stock
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)

# ------------------------------------
# KHATA REGISTER ROUTES
# ------------------------------------
@app.route('/api/khata', methods=['GET', 'OPTIONS'])
def get_khata():
    if request.method == 'OPTIONS':
        return jsonify({"status": "OK"}), 200
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS customer_khata (id SERIAL PRIMARY KEY, name VARCHAR(100), phone VARCHAR(15), amount NUMERIC(10,2), note TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        conn.commit()
        
        cur.execute("SELECT * FROM customer_khata ORDER BY id DESC;")
        records = cur.fetchall()
        cur.close()

        total_pending = sum(float(r['amount']) for r in records)
        return jsonify({"records": records, "total_pending": total_pending}), 200
    except Exception as e:
        return jsonify({"records": [], "total_pending": 0}), 200
    finally:
        if conn:
            release_db_connection(conn)

@app.route('/api/khata/add', methods=['POST', 'OPTIONS'])
def add_khata():
    if request.method == 'OPTIONS':
        return jsonify({"status": "OK"}), 200
    conn = None
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON payload received"}), 400

        name = sanitize_string(data.get('name', ''))
        phone = sanitize_string(data.get('phone', ''))
        amount = float(data.get('amount', 0))
        note = sanitize_string(data.get('note', ''))

        if not name or amount <= 0:
            return jsonify({"error": "Valid name and positive amount are required"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO customer_khata (name, phone, amount, note) VALUES (%s, %s, %s, %s);", (name, phone, amount, note))
        conn.commit()
        cur.close()

        return jsonify({"message": f"Udhaar entry added for {name}!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            release_db_connection(conn)
import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Raunak's Kirana Server on port {port}...", flush=True)
    serve(app, host='0.0.0.0', threads=16, port=port)