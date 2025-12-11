import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(basedir, 'sqlite')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(db_dir, 'indago.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class PurchaseRequest(db.Model):
    __tablename__ = 'purchase_requests'
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    estimated_cost = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='PENDING') 
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    decision_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'item_name': self.item_name,
            'quantity': self.quantity,
            'estimated_cost': self.estimated_cost,
            'status': self.status,
            'request_date': self.request_date.strftime('%Y-%m-%d %H:%M:%S'),
            'notes': self.notes
        }

# 2. Tabel WeeklyOrder (Data Pesanan Mingguan - Simulasi Tim Order)
# Ini ditambahkan agar Finance bisa melihat data pesanan
class WeeklyOrder(db.Model):
    __tablename__ = 'weekly_orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    order_menu = db.Column(db.String(100)) # Misal: "Nasi Goreng 50 porsi"
    week_number = db.Column(db.Integer) # Minggu ke-berapa
    total_value = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id,
            'customer': self.customer_name,
            'menu': self.order_menu,
            'value': self.total_value
        }

# Setup Database
with app.app_context():
    db.create_all()

    if not WeeklyOrder.query.first():
        dummy_orders = [
            WeeklyOrder(customer_name="PT Teknologi Maju", order_menu="Katering Siang (100 pax)", week_number=42, total_value=5000000),
            WeeklyOrder(customer_name="Event Wedding", order_menu="Prasmanan VIP", week_number=42, total_value=15000000)
        ]
        db.session.bulk_save_objects(dummy_orders)
        db.session.commit()
        print("Data dummy Weekly Orders berhasil dibuat.")


@app.route('/')
def index():
    return "Finance Subsystem & Order Simulation Running."

@app.route('/api/orders-weekly', methods=['GET'])
def get_orders_weekly():
    orders = WeeklyOrder.query.all()

    total_revenue = sum(o.total_value for o in orders)
    
    return jsonify({
        'week_number': 42,
        'total_revenue_potential': total_revenue,
        'orders': [o.to_dict() for o in orders]
    }), 200


@app.route('/api/purchase-request', methods=['POST'])
def create_purchase_request():
    data = request.json
    new_request = PurchaseRequest(
        item_name=data['item_name'],
        quantity=data.get('quantity', 1),
        estimated_cost=data['cost']
    )
    db.session.add(new_request)
    db.session.commit()
    return jsonify({'message': 'Request diterima', 'data': new_request.to_dict()}), 201

@app.route('/api/finance/requests', methods=['GET'])
def get_finance_requests():
    status = request.args.get('status')
    if status:
        reqs = PurchaseRequest.query.filter_by(status=status.upper()).all()
    else:
        reqs = PurchaseRequest.query.all()
    return jsonify([r.to_dict() for r in reqs])

@app.route('/api/finance/approve/<int:req_id>', methods=['POST'])
def approve_request(req_id):
    req = PurchaseRequest.query.get_or_404(req_id)

    orders = WeeklyOrder.query.all()
    total_revenue = sum(o.total_value for o in orders)
    
    if req.estimated_cost > (total_revenue * 0.5):
         return jsonify({
            'error': 'WARNING: Biaya pembelian terlalu besar dibandingkan pendapatan mingguan!',
            'total_revenue_week': total_revenue,
            'request_cost': req.estimated_cost
        }), 400

    req.status = 'APPROVED'
    req.decision_date = datetime.utcnow()
    req.notes = request.json.get('notes', 'Approved based on weekly orders')
    db.session.commit()
    
    return jsonify({'message': 'APPROVED', 'data': req.to_dict()}), 200

# REJECT Request
@app.route('/api/finance/reject/<int:req_id>', methods=['POST'])
def reject_request(req_id):
    req = PurchaseRequest.query.get_or_404(req_id)
    req.status = 'REJECTED'
    req.decision_date = datetime.utcnow()
    req.notes = request.json.get('notes', 'Rejected')
    db.session.commit()
    return jsonify({'message': 'REJECTED', 'data': req.to_dict()})

if __name__ == '__main__':
    app.run(debug=True, port=5000)