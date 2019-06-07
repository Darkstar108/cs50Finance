import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT symbol, SUM(shares) as shares FROM 'transaction' WHERE u_id = :user_id GROUP BY symbol", user_id = session["user_id"])
    user = db.execute("SELECT * FROM 'users' WHERE id = :user_id", user_id = session["user_id"])

    if len(rows) == 0:
        return render_template("index.html", rows = 0, username = user[0]["username"], cash = user[0]["cash"], total = user[0]["cash"])

    else:
        cur_price = []
        value = []
        names = []
        total = 0
        for row in rows:
            returned_quote = lookup(row["symbol"])
            cur_price.append(returned_quote["price"])
            value.append(round(returned_quote["price"] * row["shares"], 2))
            names.append(returned_quote["name"])
            total = total + round(returned_quote["price"] * row["shares"], 2)
		
		total = round(total, 2)
		
        return render_template("index.html", username = user[0]["username"], cash = user[0]["cash"], total = total, rows = rows, cur_price = cur_price, value = value, names = names)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        # Ensure positive number of shares was submitted
        elif not request.form.get("shares") or int(request.form.get("shares")) < 0:
            return apology("must provide positive number of shares", 403)

        else:
            returned_quote = lookup(request.form.get("symbol"))
            row = db.execute("SELECT * FROM users WHERE id = :user_id", user_id = session["user_id"])
            if returned_quote == None:
                return apology("symbol does not exist", 403)

            elif returned_quote["price"] * int(request.form.get("shares")) > row[0]["cash"]:
                return apology("cannot afford number of shares at current price", 403)

            else:
                db.execute("INSERT INTO 'transaction' ('t_id','u_id','symbol','shares','price') VALUES (NULL,:u_id,:symbol,:shares,:price)",
                            u_id = session["user_id"], symbol = returned_quote["symbol"], shares = int(request.form.get("shares")), price = returned_quote["price"])
                db.execute("UPDATE users SET cash = cash - :price * :shares WHERE id = :user_id",
                            price = returned_quote["price"], shares = int(request.form.get("shares")), user_id = session["user_id"])

                flash("Bought")
                return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    rows = db.execute("SELECT * FROM 'transaction' WHERE u_id = :user_id", user_id = session["user_id"])
    return render_template("history.html", rows = rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        else:
            returned_quote = lookup(request.form.get("symbol"))
            if returned_quote == None:
                return apology("symbol does not exist", 403)
            else:
                return render_template("quoted.html", symbol = returned_quote["symbol"], name = returned_quote["name"], price = returned_quote["price"])

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password confirmation", 403)

        else:
            rows = db.execute("SELECT * FROM users WHERE username = :username",
                              username=request.form.get("username"))
            if len(rows) != 0:
                return apology("username already taken", 403)

            elif request.form.get("password") != request.form.get("confirmation"):
                return apology("password must match confirmation", 403)

            else:
                db.execute("INSERT INTO users ('id','username','hash') VALUES (NULL,:username,:hash_gen)",
                            username = request.form.get("username"), hash_gen = generate_password_hash(request.form.get("password")))

            flash("Registered")
            # Redirect user to home page
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        # Ensure positive number of shares was submitted
        elif not request.form.get("shares") or int(request.form.get("shares")) < 0:
            return apology("must provide positive number of shares", 403)

        elif int(request.form.get("shares")) > (db.execute("SELECT sum(shares) as shares FROM 'transaction' WHERE u_id = :user_id and symbol = :symbol", user_id = session["user_id"], symbol = request.form.get("symbol")))[0]["shares"]:
            return apology("cannot sell more shares than owned", 403)

        else:
            returned_quote = lookup(request.form.get("symbol"))
            row = db.execute("SELECT * FROM users WHERE id = :user_id", user_id = session["user_id"])

            db.execute("INSERT INTO 'transaction' ('t_id','u_id','symbol','shares','price') VALUES (NULL,:u_id,:symbol,:shares,:price)",
                        u_id = session["user_id"], symbol = returned_quote["symbol"], shares = -1*int(request.form.get("shares")), price = returned_quote["price"])
            db.execute("UPDATE users SET cash = cash + :price * :shares WHERE id = :user_id",
                        price = returned_quote["price"], shares = int(request.form.get("shares")), user_id = session["user_id"])

            flash("Sold")
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        rows = db.execute("SELECT symbol, SUM(shares) as shares FROM 'transaction' WHERE u_id = :user_id GROUP BY symbol", user_id = session["user_id"])

        if len(rows) > 0:
            return render_template("sell.html", rows = rows)
        else:
            return apology("no shares to sell", 403)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
