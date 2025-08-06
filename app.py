from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
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
    # Expect JSON data from the frontend
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid request. No data provided.", "success": False}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required.", "success": False}), 400

    hashed_password = generate_password_hash(password)
    cur = mysql.connection.cursor()

    try:
        # Check if user already exists
        cur.execute("SELECT email FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({"message": "An account with this email already exists.", "success": False}), 409 # HTTP 409 Conflict

        # Insert new user
        cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, hashed_password))
        mysql.connection.commit()
        return jsonify({"message": "Account created successfully! Please log in.", "success": True}), 201 # HTTP 201 Created
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        print(f"DATABASE REGISTRATION ERROR: {e}")
        return jsonify({"message": "A database error occurred during registration.", "success": False}), 500
    finally:
        cur.close()

@app.route("/login", methods=["POST"])
def login():
    # Expect JSON data from the frontend
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid request. No data provided.", "success": False}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required.", "success": False}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT email, password_hash FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user"] = email  # Set user session
            # On success, tell the frontend it worked. The frontend will handle the redirect.
            return jsonify({"message": "Login successful!", "success": True}), 200
        else:
            # Invalid credentials
            return jsonify({"message": "Invalid credentials. Please try again.", "success": False}), 401 # HTTP 401 Unauthorized
    except MySQLdb.Error as e:
        print(f"DATABASE LOGIN ERROR: {e}")
        return jsonify({"message": "A database error occurred during login.", "success": False}), 500
    finally:
        cur.close()

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))  # Protect route

    user_email = session["user"]
    user_name = user_email.split('@')[0]  # Get a display name from the email
    try:
        cur = mysql.connection.cursor()

        # Fetch summary data for the logged-in user
        cur.execute("SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income, SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense FROM transactions WHERE user_email = %s", (user_email,))
        summary = cur.fetchone() or {} # Ensure summary is a dict, not None, to prevent errors
        total_income = summary.get('total_income') or 0
        total_expense = summary.get('total_expense') or 0
        balance = total_income - total_expense
        savings_rate = (balance / total_income) * 100 if total_income > 0 else 0

        # Fetch recent transactions for the logged-in user
        cur.execute("SELECT id, type, amount, category, date, description FROM transactions WHERE user_email = %s ORDER BY date DESC, id DESC LIMIT 10", (user_email,))
        transactions = cur.fetchall()

        # --- ADD THIS CODE BLOCK ---
        # Fetch financial goals for the logged-in user
        cur.execute("SELECT id, title, category, current_amount, target_amount, target_date FROM goals WHERE user_email = %s ORDER BY target_date ASC", (user_email,))
        goals = cur.fetchall()
        # --- END OF ADDED CODE BLOCK ---

        cur.close()
        # --- UPDATE THE LINE BELOW ---
        return render_template(
            "dashboard.html",
            income=total_income,
            expense=total_expense,
            balance=balance,
            transactions=transactions,
            savings_rate=savings_rate,
            user_name=user_name,
            goals=goals,
            today_date=date.today()
        )
    except MySQLdb.Error as e:
        print(f"DATABASE DASHBOARD ERROR: {e}")
        flash("Could not load dashboard data due to a database error.", "error")
        # Render the dashboard with zeroed-out data so the page doesn't crash
        return render_template("dashboard.html", income=0, expense=0, balance=0, transactions=[], savings_rate=0, user_name=session.get("user", "").split('@')[0], goals=[], today_date=date.today())

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
        try:
            data = request.get_json()
            if not data:
                return jsonify({"message": "Invalid request. No data provided.", "success": False}), 400

            # --- Data Extraction and Validation ---
            transaction_type = data.get('type')
            # Safely handle amount, converting None or other non-strings to an empty string
            amount_raw = data.get('amount')
            amount_str = str(amount_raw).strip() if amount_raw is not None else ''
            category = data.get('category')
            date = data.get('date')
            description = data.get('description', '')

            # Improved validation
            if not all([transaction_type, category, date, amount_str]):
                return jsonify({"message": "Type, Amount, Category, and Date are required fields.", "success": False}), 400

            amount = float(amount_str)

            if amount <= 0:
                return jsonify({"message": "Amount must be a positive number.", "success": False}), 400

            # --- Database Interaction ---
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO transactions (user_email, type, amount, category, date, description) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_email, transaction_type, amount, category, date, description)
            )
            mysql.connection.commit()

            cur.close()

            # Since the page redirects, we only need to send a success message.
            # No need to send back summary data that won't be used.
            return jsonify({
                "message": "Transaction added successfully!",
                "success": True
            }), 200
        except ValueError:
            return jsonify({"message": "Amount must be a valid number.", "success": False}), 400
        except MySQLdb.Error as e:
            mysql.connection.rollback()
            print(f"DATABASE TRANSACTION ERROR: {e}")
            return jsonify({
                "message": "A database error occurred. Please check your data is valid and try again.",
                "success": False
            }), 500
        except Exception as e:
            # This is a catch-all for any other unexpected errors
            mysql.connection.rollback() # Good practice to rollback on any error
            print(f"UNEXPECTED ERROR in handle_transaction: {e}")
            return jsonify({
                "message": "An internal server error occurred. Please try again later.",
                "success": False
            }), 500

    # For GET requests
    return render_template('transaction.html')

@app.route('/add-goal-form')
def add_goal_form():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template('add_goal_form.html')

@app.route('/add-goal', methods=['POST'])
def add_goal():
    if "user" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    user_email = session["user"]
    cur = None # Initialize cur to None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Invalid request. No data provided.", "success": False}), 400

        title = data.get('title')
        category = data.get('category')
        target_amount_raw = data.get('target_amount')
        current_amount_raw = data.get('current_amount', 0) # Default current amount to 0
        target_date_str = data.get('target_date')

        if not all([title, category, target_amount_raw, target_date_str]):
            return jsonify({"message": "Title, Category, Target Amount, and Target Date are required.", "success": False}), 400

        # Validate and convert data
        target_amount = float(target_amount_raw)
        current_amount = float(current_amount_raw)
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

        if target_amount <= 0:
             return jsonify({"message": "Target Amount must be a positive number.", "success": False}), 400

        cur = mysql.connection.cursor()
        # Add user_email to the INSERT statement
        cur.execute("""INSERT INTO goals (user_email, title, category, target_amount, current_amount, target_date)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (user_email, title, category, target_amount, current_amount, target_date))
        mysql.connection.commit()
        return jsonify({'success': True, 'message': 'Goal added successfully!'}), 201
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid data format for amount or date.", "success": False}), 400
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        # Log the full error to the console for your records
        print(f"DATABASE GOAL ERROR: {e}") 

        # Create a more helpful error message for the frontend
        user_facing_message = "A database error occurred. Please check the console for details."
        if app.debug:
            # When debugging, send the specific DB error string to the browser.
            # Using str(e) is crucial as the raw exception object isn't JSON serializable.
            user_facing_message = f"Database Error: {str(e)}"

        return jsonify({"message": user_facing_message, "success": False}), 500
    except Exception as e:
        # Catch any other unexpected errors to prevent a server crash
        # and ensure a JSON response is always sent for this API endpoint.
        if mysql.connection:
            mysql.connection.rollback()
        print(f"UNEXPECTED GOAL ERROR: {e}")
        return jsonify({"message": "An internal server error occurred.", "success": False}), 500
    finally:
        if cur:
            cur.close()
@app.route('/monthly-income-expense-data')
def monthly_income_expense_data():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'User not logged in'}), 401

    cur = mysql.connection.cursor()

    query = """
        SELECT 
            DATE_FORMAT(date, '%b') AS month,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expense
        FROM transactions
        WHERE user_email = %s
        GROUP BY MONTH(date)
        ORDER BY MONTH(date);
    """
    cur.execute(query, (user_email,))
    results = cur.fetchall()
    cur.close()

    data = {
        "labels": [],
        "income": [],
        "expense": []
    }

    for row in results:
        data["labels"].append(row[0])
        data["income"].append(float(row[1]))
        data["expense"].append(float(row[2]))

    return jsonify(data)
      

if __name__ == "__main__":
    app.run(debug=True)
