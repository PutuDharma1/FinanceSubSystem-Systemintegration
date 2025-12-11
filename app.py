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
    status = db.Column(db.String(20)) 
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    decision_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.String(255))

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

class WeeklyOrder(db.Model):
    __tablename__ = 'weekly_orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100))
    order_menu = db.Column(db.String(100))
    week_number = db.Column(db.Integer)
    total_value = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id,
            'customer': self.customer_name,
            'menu': self.order_menu,
            'value': self.total_value
        }

with app.app_context():
    db.create_all()
    
    if not WeeklyOrder.query.first():
        dummy_orders = [
            WeeklyOrder(
                customer_name="Walk-in Customers (Week 42)", 
                order_menu="Palm Sugar Latte & Americano (50 cups)", 
                week_number=42, 
                total_value=1250000 
            ),
            WeeklyOrder(
                customer_name="Marketing Dept Meeting", 
                order_menu="Coffee Break Package (15 Bottles)", 
                week_number=42, 
                total_value=375000
            )
        ]
        db.session.bulk_save_objects(dummy_orders)
        db.session.commit()

@app.route('/')
def index():
    return "Automated Finance Subsystem is Running."

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
def process_purchase_request():
    data = request.json
    if not data or 'item_name' not in data or 'cost' not in data:
        return jsonify({'error': 'Incomplete data'}), 400

    requested_cost = data['cost']
    
    orders = WeeklyOrder.query.all()
    total_weekly_revenue = sum(o.total_value for o in orders)
    
    budget_limit = total_weekly_revenue * 0.60 

    final_status = 'APPROVED'
    decision_note = 'Auto-approved: Within budget limit.'

    if requested_cost > budget_limit:
        final_status = 'REJECTED'
        decision_note = f'Auto-rejected: Cost {requested_cost} exceeds 60% of revenue ({total_weekly_revenue})'

    new_request = PurchaseRequest(
        item_name=data['item_name'],
        quantity=data.get('quantity', 1),
        estimated_cost=requested_cost,
        status=final_status, 
        notes=decision_note
    )
    
    db.session.add(new_request)
    db.session.commit()
    
    response_code = 201 if final_status == 'APPROVED' else 400
    
    return jsonify({
        'message': f'Request processed and {final_status}',
        'data': new_request.to_dict()
    }), response_code

@app.route('/api/finance/history', methods=['GET'])
def get_finance_history():
    reqs = PurchaseRequest.query.order_by(PurchaseRequest.request_date.desc()).all()
    return jsonify([r.to_dict() for r in reqs])

if __name__ == '__main__':
    app.run(debug=True, port=5000)