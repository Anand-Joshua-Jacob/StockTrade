import os
import datetime
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

# The default route where the user see's a list of their current hodings
# For this lab I think it would be a good idea to create another table as it would reduce the code I had to type by a huge amount.


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    symbols = []
    shrs = []
    names = []
    prices = []
    totals = []

    dictionary = db.execute("SELECT symbol, shares FROM transactions WHERE user_id = ? ", session["user_id"])

    for i in range(len(dictionary)):

        if dictionary[i]['symbol'] not in symbols:
            symbols.append(dictionary[i]['symbol'])

    for symbol in symbols:

        #ditn = db.execute("SELECT shares FROM transactions WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
        s = 0

        for ele in dictionary:

            if ele['symbol'] == symbol:

                s += ele['shares']

        shrs.append(s)

    di = []

    for i in range(len(shrs)):

        if shrs[i] == 0:

            dic = {}
            dic['symbol'] = symbols[i]
            dic['share'] = shrs[i]
            di.append(dic)

    for d in di:

        symbols.remove(d['symbol'])
        shrs.remove(d['share'])

    for symbol in symbols:
        comp = lookup(str(symbol))
        prices.append(float(comp['price']))
        names.append(comp['name'])

    for i in range(len(symbols)):
        totals.append(prices[i] * shrs[i])

    symbols.append('CASH')

    ch = float(db.execute("SELECT cash FROM users WHERE id = ? ", session["user_id"])[0]['cash'])
    totals.append(ch)

    gt = 0

    for i in range(len(totals)):
        gt += totals[i]

    shrs.append("-")
    names.append("-")
    prices.append(0)
    l = []

    for i in range(len(symbols)):
        l.append(i)

    return render_template("index.html", symbols=symbols, shrs=shrs, names=names, prices=prices, totals=totals, gt=gt, l=l)

    # db.execute("")
    # db.execute("")

# The route to login


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")

    else:

        dt = datetime.datetime.now()
        if not request.form.get('symbol'):
            return apology('Please type a symbol', 400)

        if not request.form.get('shares'):
            return apology('Please type a share', 400)

        comp = lookup(request.form.get('symbol'))

        if comp == None:
            return apology('Symbol not found in our database', 400)

        if not (request.form.get('shares')).isdigit():
            return apology('Please type a positive integer', 400)

        else:
            if not int(request.form.get('shares')) > 0:
                return apology('Please type a positive integer', 400)

        price = float(comp['price'])
        name = str(comp['name'])
        symbol = str(comp['symbol'])
        shares = int(request.form.get('shares'))
        total = price*shares
        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        if total > balance[0]['cash']:
            return apology('Not enough money')

        db.execute('UPDATE users SET cash=? WHERE id = ?', balance[0]['cash']-total,  session["user_id"])

        db.execute('INSERT INTO transactions (user_id, symbol, name, price, shares, total, datetime) VALUES (?,?,?,?,?,?,?)',
                   session["user_id"], symbol, name, price, shares, total, dt)

        return redirect("/")

# The history of transactions made by the person


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    dic = db.execute("SELECT symbol, shares, price, datetime FROM transactions WHERE user_id = ?", session["user_id"])

    return render_template("history.html", dic=dic)


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
    if request.method == "GET":
        return render_template("quote.html")

    else:

        if not request.form.get("symbol"):
            return apology("give a symbol", 400)
        comp = lookup(request.form.get("symbol"))

        if comp == None:
            return apology("Sorry we could not find this symbol in our database.", 400)

        else:
            return render_template("quoted.html", price=comp['price'], name=comp['name'])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:

        rows = db.execute("SELECT * FROM users WHERE username = ?", str(request.form.get("username")))

        un = request.form.get("username")
        ps = request.form.get("password")
        cps = request.form.get("confirmation")

        # Ensure username was submitted
        if not un:
            return apology("Must provide username", 400)

        # Ensure password was submitted
        elif not ps or not cps:
            return apology("Must provide password", 400)

        elif ps != cps:
            return apology("Password and confirmation password don't match", 400)

        elif len(rows) != 0:
            return apology("Username is already taken.", 400)

        cps = generate_password_hash(ps)

        p_key = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", un, cps)

        # Remember which user has logged in
        session["user_id"] = p_key

        # Redirect user to home page
        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    diction = db.execute("SELECT symbol, shares FROM transactions WHERE user_id = ?", session["user_id"])
    symbols = []

    for di in diction:

        if di['symbol'] not in symbols:
            symbols.append(di['symbol'])

    if request.method == "GET":

        return render_template("sell.html", symbols=symbols)

    else:

        shrs = []

        dt = datetime.datetime.now()
        if not request.form.get('symbol'):
            return apology('Please type a symbol')

        if not request.form.get('shares'):
            return apology('Please type a share')

        comp = lookup(request.form.get('symbol'))

        if comp == None:
            return apology('Symbol not found in our database')

        for symbol in symbols:

            #ditn = db.execute("SELECT shares FROM transactions WHERE user_id = ? AND symbol = ?", session["user_id"], symbol)
            s = 0

            for ele in diction:

                if ele['symbol'] == symbol:

                    s += ele['shares']

            shrs.append(s)

        if comp['symbol'] not in symbols:
            return apology("You have no stock in this company")

        for i in range(len(symbols)):

            if symbols[i] == comp['symbol'] and int(request.form.get('shares')) > shrs[i]:
                return apology("You don't have those many shares in this company")

        price = float(comp['price'])
        name = str(comp['name'])
        symbol = str(comp['symbol'])
        shares = int(request.form.get('shares'))
        total = price*shares
        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        db.execute('UPDATE users SET cash=? WHERE id = ?', balance[0]['cash']+total,  session["user_id"])

        db.execute('INSERT INTO transactions (user_id, symbol, name, price, shares, total, datetime) VALUES (?,?,?,?,?,?,?)',
                   session["user_id"], symbol, name, price, -shares, -total, dt)

        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)