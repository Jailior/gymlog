import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flaskwebgui import FlaskUI
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date

from functions import error, kg


app = Flask(__name__)
ui = FlaskUI(app)
test_env = False

app.config["TEMPLATES_AUTO_RELOAD"] = True

# session setting
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///project.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():

    if session.get("user_id") is None:
        return redirect("/login")

    trainings = db.execute("SELECT id, day FROM training WHERE user_id = ?;", session["user_id"])
    trainingIDs = []
    counter = 0

    for i in trainings:
        trainingIDs.append(trainings[counter]["id"])
        counter += 1

    exercises = db.execute("SELECT id, training_id, name, description, sets, reps, weight FROM exercise WHERE training_id IN (?);", trainingIDs)

    if trainings == []:
            return error("You have no trainings, go to setup to fix that!", "GYM BRO!")

    return render_template("index.html", trainings=trainings, exercises=exercises)




@app.route("/setup", methods=["GET", "POST"])
def setup():

    if request.method == "POST":

        day = request.form.get("day")

        if len(day) >= 1:
            db.execute("INSERT INTO training (user_id, day) VALUES (?, ?);", session["user_id"], day)
            return redirect("/")

        tday = request.form.get("tday")
        exercise = request.form.get("ename")
        desc = request.form.get("desc")
        try:
            sets = int(request.form.get("sets"))
            reps = int(request.form.get("reps"))
            weight = float(request.form.get("weight"))
        except:
            return error("missing information", 400)

        if (not tday or not exercise or not sets or not reps or not weight) and len(day) <= 0:
            return error("missing information", 400)

        if sets <= 0 or reps <= 0 or weight <= 0:
            return error("enter valid number", 400)

        tdayID = db.execute("SELECT id FROM training WHERE day = ? AND user_id = ?;", tday, session["user_id"])

        if tdayID != []:
            tdayID = tdayID[0]["id"]

        db.execute("INSERT INTO exercise (training_id, name, description, sets, reps, weight) VALUES (?, ?, ?, ?, ?, ?);", tdayID, exercise, desc, sets, reps, weight)

        return redirect("/")

    else:
        trainings = db.execute("SELECT * FROM training WHERE user_id = ?;", session["user_id"])
        return render_template("setup.html", trainings=trainings)



@app.route("/update", methods=["GET", "POST"])
def update():

    trainings = db.execute("SELECT id, day FROM training WHERE user_id = ?;", session["user_id"])
    trainingIDs = []
    counter = 0

    for i in trainings:
        trainingIDs.append(trainings[counter]["id"])
        counter += 1

    exercises = db.execute("SELECT id, training_id, name, description, sets, reps, weight FROM exercise WHERE training_id IN (?);", trainingIDs)

    if request.method == "POST":

        counter = 0
        input = 0

        for i in exercises:
            eID = exercises[counter]["id"]
            sets = request.form.get(f"{eID} sets")
            reps = request.form.get(f"{eID} reps")
            weight = request.form.get(f"{eID} weight")

            if sets != "" and reps != "" and weight != "":
                sets = int(sets)
                reps = int(reps)
                weight = float(weight)

                if sets <= 0 or reps <= 0 or weight <= 0:
                    return error("enter valid number", 400)

                db.execute("UPDATE exercise SET sets = ?, reps = ?, weight = ? WHERE id = ?;", sets, reps, weight, eID)

                today = date.today()
                d = today.strftime("%Y-%m-%d")
                db.execute("INSERT INTO log (exercise_id, sets, reps, weight, date) VALUES (?, ?, ?, ?, ?);", eID, sets, reps, weight, d)
                input += 1

            counter += 1

        if input <= 0:
            return error("enter sufficient amount of details", 400)

        return redirect("/")

    else:

        if trainings == []:
            return error("no trainings to update", 400)

        return render_template("update.html", trainings=trainings, exercises=exercises)




@app.route("/progress", methods=["GET", "POST"])
def progress():

    trainings = db.execute("SELECT id, day FROM training WHERE user_id = ?;", session["user_id"])
    trainingIDs = []
    counter = 0

    for i in trainings:
        trainingIDs.append(trainings[counter]["id"])
        counter += 1

    exercises = db.execute("SELECT id, training_id, name, description, sets, reps, weight FROM exercise WHERE training_id IN (?);", trainingIDs)
    exerciseIDs = []
    counter = 0

    for j in exercises:
        exerciseIDs.append(exercises[counter]["id"])
        counter += 1


    logs = db.execute("SELECT exercise_id, sets, reps, weight, date FROM log WHERE exercise_id IN (?);", exerciseIDs)

    if trainings == []:
            return error("You have no trainings, go to setup to fix that!", "GYM BRO!")

    return render_template("progress.html", trainings=trainings, exercises=exercises, logs=logs)


@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return error("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return error("invalid username and/or password", 403)

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


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        if not request.form.get("username"):
            return error("must provide username", 400)

        usercheck = db.execute("SELECT username FROM users;")
        print(usercheck)
        users = []
        user = 0
        if usercheck != []:
            for i in usercheck:
                users.append(usercheck[user]["username"])
                user += 1

        if request.form.get("username") in users:
            return error("username in use", 400)

        elif not request.form.get("password"):
            return error("must provide password", 400)

        elif not request.form.get("confirmation"):
            return error("must reconfirm password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return error("passwords must match", 400)

        psh = generate_password_hash(request.form.get("password"))

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?);", request.form.get("username"), psh)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("register.html")

if test_env:
    ui.run()
else:
    app.run()