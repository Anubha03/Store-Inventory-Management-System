"""
Columbia's COMS W4111.001 Introduction to Databases
Store Inventory Management System
"""
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort, session, url_for, flash
from datetime import datetime

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = os.urandom(24)  #Required for session management

# Configure a PostgreSQL connection through the environment.
DATABASEURI = os.environ["DATABASE_URL"]

engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
    """Setup database connection before each request"""
    try:
        g.conn = engine.connect()
    except:
        print("uh oh, problem connecting to database")
        import traceback
        traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    """Close database connection after each request"""
    try:
        g.conn.close()
    except Exception as e:
        pass

#Login page
@app.route('/')
def index():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
    #To handle login authentication
    employee_id = request.form.get('employee_id')
    password = request.form.get('password')
    
    if not employee_id or not password:
        flash('Please enter both Employee ID and Password', 'error')
        return redirect('/')
    
    try:
        #To check credentials
        query = text("SELECT Employee_ID, Emp_Name, Role FROM Employee WHERE Employee_ID = :emp_id AND Password = :pwd")
        result = g.conn.execute(query, {"emp_id": employee_id, "pwd": password})
        user = result.fetchone()
        
        if user:
            #Storing user info in session
            session['employee_id'] = user[0]
            session['employee_name'] = user[1]
            session['employee_role'] = user[2]
            return redirect('/home')
        else:
            flash('Invalid Employee ID or Password', 'error')
            return redirect('/')
    except Exception as e:
        print(f"Login error: {e}")
        flash('An error occurred during login', 'error')
        return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect('/')

#Home page
@app.route('/home')
def home():
    #Going to home page after login
    if 'employee_id' not in session:
        return redirect('/')
    
    return render_template("home.html", 
                         name=session['employee_name'],
                         role=session['employee_role'])

#Adding new product
@app.route('/add_product')
def add_product_page():
    if 'employee_id' not in session:
        return redirect('/')
    
    #Getting categories and shelves for dropdowns
    categories = g.conn.execute(text("SELECT Category_ID, Category_Name FROM Category ORDER BY Category_Name")).fetchall()
    shelves = g.conn.execute(text("SELECT Shelf_ID, Location FROM Shelf ORDER BY Shelf_ID")).fetchall()
    
    return render_template("add_product.html", categories=categories, shelves=shelves)

@app.route('/add_product_submit', methods=['POST'])
def add_product_submit():
    if 'employee_id' not in session:
        return redirect('/')
    
    try:
        product_name = request.form['product_name']
        category_id = request.form['category_id']
        shelf_id = request.form['shelf_id']
        price = request.form['price']
        quantity = request.form['quantity']
        expiration = request.form.get('expiration') or None

        #Error handling if wrong data type is entered
        try:
            category_id = int(category_id)
            shelf_id = int(shelf_id)
            price = float(price)
            quantity = int(quantity)
        except ValueError:
            flash('Error: Please enter correct data types. Category ID, Shelf ID, and Quantity must be numbers. Price must be a decimal number.', 'error')
            return redirect('/add_product')
        
        if price < 0 or quantity < 0:
            flash('Error: Price and Quantity cannot be negative.', 'error')
            return redirect('/add_product')

        
        #Getting next product ID
        max_id = g.conn.execute(text("SELECT COALESCE(MAX(Product_ID), 0) FROM Product")).fetchone()[0]
        new_id = max_id + 1
        
        #Inserting product
        query = text("""
            INSERT INTO Product (Product_ID, Product_Name, Category_ID, Shelf_ID, Price, Quantity, Expiration)
            VALUES (:pid, :pname, :cid, :sid, :price, :qty, :exp)
        """)
        g.conn.execute(query, {
            "pid": new_id, "pname": product_name, "cid": category_id,
            "sid": shelf_id, "price": price, "qty": quantity, "exp": expiration
        })
        
        #Logging stock movement
        max_mov_id = g.conn.execute(text("SELECT COALESCE(MAX(Movement_ID), 0) FROM Stock_Movement")).fetchone()[0]
        mov_query = text("""
            INSERT INTO Stock_Movement (Movement_ID, Product_ID, Employee_ID, Shelf_ID, DateTime, Quantity_Change, Reason)
            VALUES (:mid, :pid, :eid, :sid, :dt, :qty, :reason)
        """)
        g.conn.execute(mov_query, {
            "mid": max_mov_id + 1, "pid": new_id, "eid": session['employee_id'],
            "sid": shelf_id, "dt": datetime.now(), "qty": quantity, "reason": "Initial Stock"
        })
        
        g.conn.commit()
        flash(f'Product "{product_name}" added successfully!', 'success')
    except Exception as e:
        print(f"Error adding product: {e}")
        flash('Error adding product', 'error')
    
    return redirect('/add_product')

#Deleting a product
@app.route('/delete_product')
def delete_product_page():
    if 'employee_id' not in session:
        return redirect('/')
    
    products = g.conn.execute(text("""
        SELECT p.Product_ID, p.Product_Name, c.Category_Name, p.Quantity
        FROM Product p
        JOIN Category c ON p.Category_ID = c.Category_ID
        ORDER BY p.Product_Name
    """)).fetchall()
    
    return render_template("delete_product.html", products=products)

@app.route('/delete_product_submit', methods=['POST'])
def delete_product_submit():
    if 'employee_id' not in session:
        return redirect('/')
    
    try:
        product_id = request.form['product_id']

        #Error handling
        try:
            product_id = int(product_id)
        except ValueError:
            flash('Error: Product ID must be a number.', 'error')
            return redirect('/delete_product')

        #Deleting stock movements first due to foreign key constraint
        g.conn.execute(text("DELETE FROM Stock_Movement WHERE Product_ID = :pid"), {"pid": product_id})
        
        #Deleting product
        g.conn.execute(text("DELETE FROM Product WHERE Product_ID = :pid"), {"pid": product_id})
        
        g.conn.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        print(f"Error deleting product: {e}")
        flash('Error deleting product', 'error')
    
    return redirect('/delete_product')

#Updating quantity
@app.route('/update_quantity')
def update_quantity_page():    
    if 'employee_id' not in session:
        return redirect('/')
    
    products = g.conn.execute(text("""
        SELECT p.Product_ID, p.Product_Name, p.Quantity, s.Shelf_ID, s.Location
        FROM Product p
        JOIN Shelf s ON p.Shelf_ID = s.Shelf_ID
        ORDER BY p.Product_Name
    """)).fetchall()
    
    return render_template("update_quantity.html", products=products)

@app.route('/update_quantity_submit', methods=['POST'])
def update_quantity_submit():
    if 'employee_id' not in session:
        return redirect('/')
    
    try:
        product_id = request.form['product_id']
        quantity_change = int(request.form['quantity_change'])
        reason = request.form['reason']

        #Error handling
        try:
            product_id = int(product_id)
            quantity_change = int(quantity_change)
        except ValueError:
            flash('Error: Product ID and Quantity Change must be numbers.', 'error')
            return redirect('/update_quantity')
        
        #Getting current quantity and shelf
        result = g.conn.execute(text("SELECT Quantity, Shelf_ID FROM Product WHERE Product_ID = :pid"), 
                               {"pid": product_id}).fetchone()
        current_qty = result[0]
        shelf_id = result[1]
        new_qty = current_qty + quantity_change
        
        if new_qty < 0:
            flash('Error: Quantity cannot be negative', 'error')
            return redirect('/update_quantity')
        
        #Updating product quantity
        g.conn.execute(text("UPDATE Product SET Quantity = :qty WHERE Product_ID = :pid"),
                      {"qty": new_qty, "pid": product_id})
        
        #Inserting stock movement
        max_mov_id = g.conn.execute(text("SELECT COALESCE(MAX(Movement_ID), 0) FROM Stock_Movement")).fetchone()[0]
        mov_query = text("""
            INSERT INTO Stock_Movement (Movement_ID, Product_ID, Employee_ID, Shelf_ID, DateTime, Quantity_Change, Reason)
            VALUES (:mid, :pid, :eid, :sid, :dt, :qty, :reason)
        """)
        g.conn.execute(mov_query, {
            "mid": max_mov_id + 1, "pid": product_id, "eid": session['employee_id'],
            "sid": shelf_id, "dt": datetime.now(), "qty": quantity_change, "reason": reason
        })
        
        g.conn.commit()
        flash(f'Quantity updated successfully! New quantity: {new_qty}', 'success')
    except Exception as e:
        print(f"Error updating quantity: {e}")
        flash('Error updating quantity', 'error')
    
    return redirect('/update_quantity')

#Searching products
@app.route('/search')
def search_page():
    if 'employee_id' not in session:
        return redirect('/')
    
    #Getting options for filters
    categories = g.conn.execute(text("SELECT Category_ID, Category_Name FROM Category ORDER BY Category_Name")).fetchall()
    shelves = g.conn.execute(text("SELECT Shelf_ID, Location FROM Shelf ORDER BY Shelf_ID")).fetchall()
    
    #Getting filter parameters
    product_name = request.args.get('product_name', '')
    category_id = request.args.get('category_id', '')
    shelf_id = request.args.get('shelf_id', '')
    threshold = request.args.get('threshold', '')

    #Error handling
    if category_id:
        try:
            category_id = int(category_id)
        except ValueError:
            flash('Error: Category ID must be a number.', 'error')
            return render_template("search.html", products=[], categories=categories, 
                                 shelves=shelves, filters=request.args)
    
    if shelf_id:
        try:
            shelf_id = int(shelf_id)
        except ValueError:
            flash('Error: Shelf ID must be a number.', 'error')
            return render_template("search.html", products=[], categories=categories, 
                                 shelves=shelves, filters=request.args)

    if threshold:
        try:
            threshold = int(threshold)
            if threshold < 0:
                flash('Error: Threshold cannot be negative.', 'error')
                return render_template("search.html", products=[], categories=categories, 
                                     shelves=shelves, filters=request.args)
        except ValueError:
            flash('Error: Threshold must be a number.', 'error')
            return render_template("search.html", products=[], categories=categories, 
                                 shelves=shelves, filters=request.args)
    
    #Building the query
    query = """
        SELECT p.Product_ID, p.Product_Name, p.Quantity, c.Category_Name, 
               s.Shelf_ID, s.Location, p.Expiration, p.Price
        FROM Product p
        JOIN Category c ON p.Category_ID = c.Category_ID
        JOIN Shelf s ON p.Shelf_ID = s.Shelf_ID
        WHERE 1=1
    """
    params = {}
    
    if product_name:
        query += " AND LOWER(p.Product_Name) LIKE LOWER(:pname)"
        params['pname'] = f'%{product_name}%'
    if category_id:
        query += " AND p.Category_ID = :cid"
        params['cid'] = category_id
    if shelf_id:
        query += " AND p.Shelf_ID = :sid"
        params['sid'] = shelf_id
    if threshold:
        query += " AND p.Quantity <= :threshold"
        params['threshold'] = threshold
    
    query += " ORDER BY p.Product_Name"
    
    products = g.conn.execute(text(query), params).fetchall()
    
    return render_template("search.html", products=products, categories=categories, 
                         shelves=shelves, filters=request.args)
#Employee action log
@app.route('/my_log')
def my_log():
    if 'employee_id' not in session:
        return redirect('/')
    
    query = text("""
        SELECT sm.Movement_ID, p.Product_Name, sm.DateTime, sm.Quantity_Change, 
               sm.Reason, s.Location
        FROM Stock_Movement sm
        JOIN Product p ON sm.Product_ID = p.Product_ID
        JOIN Shelf s ON sm.Shelf_ID = s.Shelf_ID
        WHERE sm.Employee_ID = :eid
        ORDER BY sm.DateTime DESC
    """)
    
    logs = g.conn.execute(query, {"eid": session['employee_id']}).fetchall()
    
    return render_template("my_log.html", logs=logs)

#Stock history
@app.route('/stock_history')
def stock_history_page():
    if 'employee_id' not in session:
        return redirect('/')
    
    products = g.conn.execute(text("SELECT Product_ID, Product_Name FROM Product ORDER BY Product_Name")).fetchall()
    
    product_id = request.args.get('product_id', '')
    history = []
    
    if product_id:
        #Error handling
        try:
            product_id = int(product_id)
        except ValueError:
            flash('Error: Product ID must be a number.', 'error')
            return render_template("stock_history.html", products=products, history=[], 
                                 selected_product='')
        
        try:
            query = text("""
                SELECT sm.Movement_ID, e.Employee_ID, e.Emp_Name, sm.DateTime, sm.Quantity_Change, 
                       sm.Reason, s.Location
                FROM Stock_Movement sm
                JOIN Employee e ON sm.Employee_ID = e.Employee_ID
                JOIN Shelf s ON sm.Shelf_ID = s.Shelf_ID
                WHERE sm.Product_ID = :pid
                ORDER BY sm.DateTime DESC
            """)
            history = g.conn.execute(query, {"pid": product_id}).fetchall()
        except Exception as e:
            print(f"Stock history error: {e}")
            flash('Error retrieving stock history. Please try again.', 'error')
    
    return render_template("stock_history.html", products=products, history=history, 
                         selected_product=product_id)

if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        """Run the server"""
        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()
