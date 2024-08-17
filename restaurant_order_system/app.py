from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    dish_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/', methods=['GET', 'POST'])
def order_form():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        dish_name = request.form['dish_name']
        quantity = request.form['quantity']

        if not customer_name or not dish_name or not quantity:
            flash('All fields are required!', 'error')
        elif not quantity.isdigit() or int(quantity) < 1:
            flash('Quantity must be a positive number!', 'error')
        else:
            new_order = Order(
                customer_name=customer_name,
                dish_name=dish_name,
                quantity=int(quantity)
            )
            db.session.add(new_order)
            db.session.commit()
            flash('Order placed successfully!', 'success')
            return redirect(url_for('view_orders'))

    return render_template('order_form.html')

@app.route('/orders')
def view_orders():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    customer_name = request.args.get('customer_name', '')
    dish_name = request.args.get('dish_name', '')
    
    sort_by = request.args.get('sort_by', 'date_desc')
    sort_column = Order.order_date.desc()
    if sort_by == 'date_asc':
        sort_column = Order.order_date.asc()
    elif sort_by == 'quantity_desc':
        sort_column = Order.quantity.desc()
    elif sort_by == 'quantity_asc':
        sort_column = Order.quantity.asc()
    
    query = Order.query
    if customer_name:
        query = query.filter(Order.customer_name.ilike(f'%{customer_name}%'))
    if dish_name:
        query = query.filter(Order.dish_name.ilike(f'%{dish_name}%'))
    
    query = query.order_by(sort_column)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    orders = pagination.items
    
    total_orders = Order.query.count()
    total_revenue = db.session.query(func.sum(Order.quantity * 10)).scalar() or 0
    top_dish = db.session.query(Order.dish_name, func.count(Order.id).label('count')).group_by(Order.dish_name).order_by(func.count(Order.id).desc()).first()
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    chart_data = db.session.query(
        func.date(Order.order_date).label('date'),
        func.count(Order.id).label('count')
    ).filter(Order.order_date >= thirty_days_ago).group_by(func.date(Order.order_date)).all()
    
    chart_labels = [str(row.date) for row in chart_data]
    chart_values = [row.count for row in chart_data]

    return render_template('view_orders.html', 
                           orders=orders, 
                           pagination=pagination,
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           top_dish=top_dish.dish_name if top_dish else 'N/A',
                           chart_labels=chart_labels,
                           chart_data=chart_values)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)