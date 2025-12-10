from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('indago.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS finances
                 (id INTEGER PRIMARY KEY, amount INTEGER, status TEXT, order_id INTEGER)''')
    conn.commit()
    conn.close()

@app.route('/create-invoice', methods=['POST'])
def create_invoice():
    data = request.json
    order_id = data.get('order_id')
    amount = data.get('amount')
    if not order_id or not amount:
        return jsonify({"error": "Missing data"}), 400
    
    conn = sqlite3.connect('indago.db')
    c = conn.cursor()
    c.execute("INSERT INTO finances (amount, status, order_id) VALUES (?, ?, ?)",
              (amount, 'paid', order_id))  # Mock payment
    conn.commit()
    conn.close()
    return jsonify({"status": "Invoice created"})

@app.route('/reconcile', methods=['POST'])
def reconcile():
    # For MVP, simple sum of finances
    conn = sqlite3.connect('indago.db')
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM finances WHERE status = 'paid'")
    total = c.fetchone()[0] or 0
    conn.close()
    return jsonify({"total_reconciled": total})

@app.route('/report', methods=['GET'])
def generate_report():
    conn = sqlite3.connect('indago.db')
    c = conn.cursor()
    c.execute("SELECT order_id, amount FROM finances")
    finances = [{'order_id': row[0], 'amount': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify({"report": finances})

if __name__ == '__main__':
    init_db()
    app.run(port=5003)