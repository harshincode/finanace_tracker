from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mysqldb import MySQLdb

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Needed for session
CORS(app)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'hd@123'  # replace with your password
app.config['MYSQL_DB'] = 'finance_tracker'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # Makes query results easier to work with

mysql = MySQL(app)

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
    cur = mysql.connection.cursor()

    try:
        # Check if user already exists
        cur.execute("SELECT email FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            flash("An account with this email already exists.", "error")
            return redirect(url_for('signup_page'))

        # Insert new user
        cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, hashed_password))
        mysql.connection.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('home'))  # Redirect to login page on success
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        print(f"DATABASE REGISTRATION ERROR: {e}") # This will print the error to your console
        flash("A database error occurred. Please try again.", "error")
        return redirect(url_for('signup_page'))
    finally:
        cur.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    cur = mysql.connection.cursor()
    cur.execute("SELECT email, password_hash FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()

    if user and check_password_hash(user['password_hash'], password):
        session["user"] = email  # Set user session
        return jsonify({"message": "Login successful!", "redirect": "/dashboard"}), 200

    return jsonify({"message": "Invalid credentials"}), 401

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))  # Protect route

    user_email = session["user"]
    cur = mysql.connection.cursor() # This will now be a DictCursor

    # Fetch summary data for the logged-in user
    cur.execute("SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income, SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense FROM transactions WHERE user_email = %s", (user_email,))
    summary = cur.fetchone()
    total_income = summary['total_income'] or 0
    total_expense = summary['total_expense'] or 0
    balance = total_income - total_expense

    # Fetch recent transactions for the logged-in user
    cur.execute("SELECT id, type, amount, category, date, description FROM transactions WHERE user_email = %s ORDER BY date DESC, id DESC LIMIT 10", (user_email,))
    transactions = cur.fetchall()

    cur.close()
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
        try: # This block now covers the entire operation
            transaction_type = data['type']
            amount_str = data.get('amount', '').strip()
            amount = float(amount_str) if amount_str else 0.0
            category = data['category']
            date = data['date']
            description = data.get('description', '')

            # Basic validation
            if not all([transaction_type, category, date]):
                return jsonify({"message": "Type, category, and date are required fields."}), 400
            if amount <= 0:
                return jsonify({"message": "Amount must be a positive number."}), 400

            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO transactions (user_email, type, amount, category, date, description) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_email, transaction_type, amount, category, date, description)
            )
            mysql.connection.commit()

            # Fetch totals for the specific user
            cur.execute("SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income, SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense FROM transactions WHERE user_email = %s", (user_email,))
            summary = cur.fetchone() # summary is now a dictionary
            total_income = summary['total_income'] or 0
            total_expense = summary['total_expense'] or 0
            balance = total_income - total_expense
            cur.close()

            return jsonify({
                "message": "Transaction added successfully!", 
                "income": total_income, 
                "expense": total_expense, 
                "balance": balance,
                "success": True
            }), 200
        except Exception as e:
            # Log the actual error to your terminal for debugging
            print(f"DATABASE ERROR: {e}")
            mysql.connection.rollback() # Important to rollback on failure
            return jsonify({
                "message": "An error occurred while saving the transaction. Please check your data.",
                "success": False
            }), 500

    # For GET requests
    return render_template('transaction.html')

if __name__ == "__main__":
    app.run(debug=True)
