import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
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

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Display the entries in the database on index.html
    #Query for users cash in table users
    usercash = db.execute("SELECT cash FROM users WHERE id =?", session["user_id"])[0]["cash"]

    #Query for users data in table transactions
    folio = db.execute("SELECT symbol, stock_name, price, SUM(shares) as sum_shares FROM transactions WHERE user_id =? GROUP BY symbol", session["user_id"])

    #update shares according to current price, not to the price when bought
    #symbols = db.execute("SELECT DISTINCT symbol FROM transactions WHERE user_id =?", session["user_id"])
    #for i in symbols:
        #currentprice = lookup(symbols.i)
        #item_price = lookup(symbol)["price"]

    #Calculate total
    total = usercash

    #Grand Total
    for row in folio:
        total += lookup(row["symbol"])["price"] * row["sum_shares"]

    #render page
    return render_template("index.html", usercash=usercash, folio=folio, usd=usd, total=total, lookup = lookup)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        symbol = request.form.get("symbol").upper()
        stock = lookup(symbol)

        if not symbol:
            return apology("Please enter a symbol")

        elif not stock:
            return apology("Please enter a valid symbol")

        amount = request.form.get("shares")
        amount_int = int(amount)

        if not amount:
            return apology("Please enter number of shares")

        elif isinstance(amount_int, int) == False:
            return apology("Please enter a correct integer")

        elif amount_int <= 0:
            return apology("Please enter a postive number")

        user_id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id =?", user_id)[0]["cash"]

        stock_name = stock["name"]
        stock_price = stock["price"]

        total_price = stock_price * float(amount)


        if total_price > cash:
            return apology("Not enough cash")

        else:
            db.execute("UPDATE users SET cash = ? WHERE id =?", cash - total_price, session["user_id"])

            # create entry for bought stock -> db.execute("INSERT INTO transactions")
            db.execute("INSERT INTO transactions (user_id, stock_name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)", user_id, stock_name, amount, stock_price, "buy", symbol)
            # Redirect user to home page
            return redirect("/")


    else:

        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    #Query for users data in table transactions
    portfolio = db.execute("SELECT symbol, shares, price, time FROM transactions WHERE user_id =?", session["user_id"])

    return render_template("history.html", portfolio=portfolio, usd=usd)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

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


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        symbol = request.form.get("symbol")

        if not symbol:
            return apology("Please enter a symbol")

        stock = lookup(symbol)

        if not stock:
            return apology("Please enter a valid symbol")

        return render_template("quoteD.html", stock = stock, usd_func=usd)

    # User reached route via GET
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        #Access form data:
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirmation")

        # Ensure username does not already exist
        userslist = db.execute("SELECT username FROM users")
        for i in userslist:
            if username == i["username"]:
                return apology("username already exists")


        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        #Check that the user typed in password correctly:
        elif password != confirm:

            #return apology and redirect to register.html again
            return apology("password and confirmation do not match")
            return render_template("register.html")

        #Hash user´s password
        else:
            hash = generate_password_hash(password)

            #insert data into database
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)

            # Redirect user to login form
            return redirect("/")

    elif request.method == "GET":

        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        symbol = request.form.get("symbol")
        stock = lookup(symbol)

        if not symbol:
            return apology("Please enter a symbol")

        elif not stock:
            return apology("Please enter a valid symbol")

        #for i in available_symbols:
            #if symbol not in i["symbol"]:
                #return apology("Please check index for available shares")

        amount = int(request.form.get("shares"))
        sell_amount = 0 - int(amount)

        if amount <= 0: #or amount > available_shares:
            return apology("Please enter valid number of shares")

        item_price = lookup(symbol)["price"]
        item_name = lookup(symbol)["name"]

        available_shares = db.execute("SELECT shares FROM transactions WHERE symbol = ? AND user_id =? GROUP BY symbol", symbol, session["user_id"])[0]["shares"]

        if available_shares < amount:
            return apology("Please check available shares")

        else:

            user_id = session["user_id"]
            cash = db.execute("SELECT cash FROM users WHERE id =?", user_id)[0]["cash"]

            stock_name = stock["name"]
            stock_price = stock["price"]

            total_price = stock_price * float(amount)


            #Update users cash
            db.execute("UPDATE users SET cash = ? WHERE id =?", cash + total_price, session["user_id"])

            # create entry for sold stock
            db.execute("INSERT INTO transactions (user_id, stock_name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)", user_id, stock_name, sell_amount, stock_price, "sell", symbol)
            # Redirect user to home page
            return redirect("/")

    else:
        symbols = db.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol", session["user_id"])

        return render_template("sell.html", symbols=symbols)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
