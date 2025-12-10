from flask import Flask, request, jsonify, send_from_directory
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB = "indago.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")



# -------------------------------------------------
# INIT DATABASE
# -------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 1. Payment Gateway settlements
    c.execute('''
        CREATE TABLE IF NOT EXISTS payment_gateway_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            orders TEXT,
            amount INTEGER,
            method TEXT,
            settled_at TEXT,
            reference TEXT
        )
    ''')

    # 2. Invoices created by Finance
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT,
            supplier_id TEXT,
            details_json TEXT,
            total_amount INTEGER,
            due_date TEXT,
            created_at TEXT
        )
    ''')

    # 3. Procurement logs from Inventory subsystem
    c.execute('''
        CREATE TABLE IF NOT EXISTS procurement_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            procurement_id TEXT,
            supplier_id TEXT,
            items_json TEXT,
            total_cost INTEGER,
            timestamp TEXT
        )
    ''')

    # 4. Supplier payments
    c.execute('''
        CREATE TABLE IF NOT EXISTS supplier_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT,
            procurement_id TEXT,
            amount INTEGER,
            reference TEXT,
            paid_at TEXT
        )
    ''')

    # 5. Raw material consumption logs from Kitchen subsystem
    c.execute('''
        CREATE TABLE IF NOT EXISTS raw_material_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT,
            qty_consumed INTEGER,
            batch_id TEXT,
            timestamp TEXT
        )
    ''')

    conn.commit()
    conn.close()

@app.route("/ui")
def ui_home():
    return send_from_directory(UI_DIR, "index.html")

@app.route("/ui/<path:filename>")
def ui_files(filename):
    return send_from_directory(UI_DIR, filename)

# =====================================================
# 1) POST /api/receivePaymentGateway
# =====================================================
@app.route("/api/receivePaymentGateway", methods=["POST"])
def receive_payment_gateway():
    data = request.get_json()
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        INSERT INTO payment_gateway_logs
        (transaction_id, orders, amount, method, settled_at, reference)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data.get("transactionId"),
        ",".join(data.get("orders", [])),
        data.get("amount"),
        data.get("method"),
        data.get("settledAt"),
        data.get("reference")
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "RECEIVED"}), 201


# =====================================================
# 2) GET /api/getSalesReport   (proxies Sales subsystem)
# =====================================================
@app.route("/api/getSalesReport", methods=["GET"])
def get_sales_report():
    # This assumes the Sales subsystem is running on port 5000
    # If different port, change here.
    import requests

    try:
        resp = requests.get("http://127.0.0.1:5000/api/reportSales",
                            params=request.args)
        return jsonify(resp.json())
    except:
        return jsonify({"error": "Sales subsystem unavailable"}), 503


# =====================================================
# 3) GET /api/generateFinanceReport
# =====================================================
@app.route("/api/generateFinanceReport", methods=["GET"])
def generate_finance_report():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Count payment gateway settlements
    c.execute("SELECT COUNT(*) FROM payment_gateway_logs")
    total_pg_logs = c.fetchone()[0]

    # Count procurement logs
    c.execute("SELECT COUNT(*) FROM procurement_logs")
    procurement_count = c.fetchone()[0]

    # Count supplier payments
    c.execute("SELECT COUNT(*) FROM supplier_payments")
    supplier_payment_count = c.fetchone()[0]

    # Raw material logs
    c.execute("SELECT sku, qty_consumed, batch_id, timestamp FROM raw_material_logs")
    raw_logs = [
        {"sku": r[0], "qty": r[1], "batch": r[2], "timestamp": r[3]}
        for r in c.fetchall()
    ]

    conn.close()

    report = {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "salesSummary": {
            "totalPaymentGatewayLogs": total_pg_logs,
            "procurementCount": procurement_count,
            "supplierPaymentCount": supplier_payment_count
        },
        "rawMaterialLogs": raw_logs
    }

    return jsonify(report)


# =====================================================
# 4) POST /api/createPaymentInvoice
# =====================================================
@app.route("/api/createPaymentInvoice", methods=["POST"])
def create_payment_invoice():
    data = request.get_json()

    invoice_id = f"INV-{int(datetime.utcnow().timestamp())}"

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        INSERT INTO invoices
        (invoice_id, supplier_id, details_json, total_amount, due_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        invoice_id,
        data.get("supplierId"),
        str(data.get("details", [])),
        data.get("totalAmount"),
        data.get("dueDate"),
        datetime.utcnow().isoformat() + "Z"
    ))

    conn.commit()
    conn.close()

    return jsonify({"invoiceId": invoice_id}), 201


# =====================================================
# 5) GET /api/getRawMaterialLog
# =====================================================
@app.route("/api/getRawMaterialLog", methods=["GET"])
def get_raw_material_log():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT sku, qty_consumed, batch_id, timestamp FROM raw_material_logs")
    result = [
        {"sku": r[0], "qtyConsumed": r[1], "batchId": r[2], "timestamp": r[3]}
        for r in c.fetchall()
    ]

    conn.close()
    return jsonify(result)


# =====================================================
# 6) POST /api/recordProcurement
# =====================================================
@app.route("/api/recordProcurement", methods=["POST"])
def record_procurement():
    data = request.get_json()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        INSERT INTO procurement_logs
        (procurement_id, supplier_id, items_json, total_cost, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get("procurementId"),
        data.get("supplierId"),
        str(data.get("items", [])),
        data.get("totalCost"),
        data.get("timestamp")
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "RECORDED"}), 201


# =====================================================
# 7) POST /api/paySupplier
# =====================================================
@app.route("/api/paySupplier", methods=["POST"])
def pay_supplier():
    data = request.get_json()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''
        INSERT INTO supplier_payments
        (supplier_id, procurement_id, amount, reference, paid_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get("supplierId"),
        data.get("procurementId"),
        data.get("amount"),
        data.get("reference"),
        datetime.utcnow().isoformat() + "Z"
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "PAID"}), 201


# =====================================================
# RUN SERVER
# =====================================================
if __name__ == "__main__":
    init_db()
    app.run(port=5003, debug=True)
