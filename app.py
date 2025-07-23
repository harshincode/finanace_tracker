from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Needed for session
CORS(app)

# Use SQLite for simplicity
DATABASE = 'finance_tracker.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This allows dict-like access to rows
    return conn

def init_database():
    """Initialize the SQLite database with required tables"""
    conn = get_db_connection()
    
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create transactions table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date DATE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# Initialize database when app starts
init_database()

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/register", methods=["POST"])
def register():
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("Email and password are required.", "error")
        return redirect(url_for('signup_page'))

    hashed_password = generate_password_hash(password)

    try:
        conn = get_db_connection()
        
        # Check if user already exists
        existing_user = conn.execute("SELECT email FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            flash("An account with this email already exists.", "error")
            conn.close()
            return redirect(url_for('signup_page'))

        # Insert new user
        conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hashed_password))
        conn.commit()
        conn.close()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('home'))  # Redirect to login page on success
    except Exception as e:
        print(f"DATABASE REGISTRATION ERROR: {e}") # This will print the error to your console
        flash("A database error occurred. Please try again.", "error")
        return redirect(url_for('signup_page'))

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    user = conn.execute("SELECT email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session["user"] = email  # Set user session
        return jsonify({"message": "Login successful!", "redirect": "/dashboard"}), 200

    return jsonify({"message": "Invalid credentials"}), 401

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))  # Protect route

    user_email = session["user"]
    conn = get_db_connection()

    # Fetch summary data for the logged-in user
    summary = conn.execute("""
        SELECT 
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income, 
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense 
        FROM transactions 
        WHERE user_email = ?
    """, (user_email,)).fetchone()
    
    total_income = summary['total_income'] or 0
    total_expense = summary['total_expense'] or 0
    balance = total_income - total_expense

    # Fetch recent transactions for the logged-in user
    transactions = conn.execute("""
        SELECT id, type, amount, category, date, description 
        FROM transactions 
        WHERE user_email = ? 
        ORDER BY date DESC, id DESC 
        LIMIT 10
    """, (user_email,)).fetchall()

    conn.close()
    return render_template("dashboard.html", income=total_income, expense=total_expense, balance=balance, transactions=transactions)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


# In your main Python file (e.g., app.py)
@app.route('/transaction', methods=['GET', 'POST'])
def handle_transaction():
    if "user" not in session:
        return redirect(url_for("home"))  # Protect route

    user_email = session["user"]

    if request.method == 'POST':
        data = request.get_json()
        
        # Enhanced debugging - print received data
        print(f"=== TRANSACTION DEBUG INFO ===")
        print(f"User email: {user_email}")
        print(f"Received data: {data}")
        
        try:
            # Validate input data exists
            if not data:
                print("ERROR: No data received")
                return jsonify({"message": "No data received", "success": False}), 400
            
            # Extract and validate data
            transaction_type = data.get('type')
            amount = data.get('amount')
            category = data.get('category')
            date = data.get('date')
            description = data.get('description', '')
            
            print(f"Parsed data - Type: {transaction_type}, Amount: {amount}, Category: {category}, Date: {date}")
            
            # Basic validation
            if not transaction_type:
                return jsonify({"message": "Transaction type is required", "success": False}), 400
            if not category:
                return jsonify({"message": "Category is required", "success": False}), 400
            if not date:
                return jsonify({"message": "Date is required", "success": False}), 400
            if not amount or float(amount) <= 0:
                return jsonify({"message": "Amount must be a positive number", "success": False}), 400

            # Convert amount to float
            amount = float(amount)
            
            print(f"Opening database connection...")
            conn = get_db_connection()
            
            # Test database connection by checking if table exists
            table_check = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='transactions'
            """).fetchone()
            
            if not table_check:
                print("ERROR: transactions table does not exist")
                conn.close()
                return jsonify({"message": "Database table 'transactions' not found. Please create the database schema.", "success": False}), 500
            
            # Check table structure
            columns = conn.execute("PRAGMA table_info(transactions)").fetchall()
            print(f"Table structure: {[dict(col) for col in columns]}")
            
            print(f"Inserting transaction...")
            conn.execute("""
                INSERT INTO transactions (user_email, type, amount, category, date, description) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_email, transaction_type, amount, category, date, description))
            conn.commit()
            print(f"Transaction inserted successfully")

            # Fetch totals for the specific user
            print(f"Fetching updated totals...")
            summary = conn.execute("""
                SELECT 
                    SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income, 
                    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense 
                FROM transactions 
                WHERE user_email = ?
            """, (user_email,)).fetchone()
            
            total_income = summary['total_income'] or 0
            total_expense = summary['total_expense'] or 0
            balance = total_income - total_expense
            conn.close()
            
            print(f"Success! Income: {total_income}, Expense: {total_expense}, Balance: {balance}")
            print(f"=== END DEBUG INFO ===")

            return jsonify({
                "message": "Transaction added successfully!", 
                "income": total_income, 
                "expense": total_expense, 
                "balance": balance,
                "success": True
            }), 200
            
        except Exception as e:
            print(f"DATABASE ERROR: {e}")
            print(f"Error type: {type(e)}")
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass
            return jsonify({
                "message": f"An error occurred: {str(e)}",
                "success": False
            }), 500

    # For GET requests
    return render_template('transaction.html')

if __name__ == "__main__":
    app.run(debug=True)
