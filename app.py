from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "karens_secret_key" #required to use sessions
conn = None

def get_db_conn(): #whenever I need to connect to db, I can just call this function
    conn = sqlite3.connect('database.db') #connect to the db file
    conn.row_factory = sqlite3.Row #row factory allows named access
    return conn

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET": #the if, try, except, finally are used for error handling so nothing craches :)
        return render_template("login.html")
    email = request.form.get("email")
    password = request.form.get("password")
    db = None #initialize to prevent crashing
    try: #connect to the db and check if the user exists
        db = get_db_conn() #get the connection
        cursor = db.cursor() #create a cursor to do the sql handling
        cursor.execute("SELECT * FROM teachers where email=? AND password=?" (email, password))
        user = cursor.fetchone() 
        if user:
            #if teacher is found, save their info in session and direct them to the home page
            #sessions help keep track who is logged in when they navigate through diff pages, ITS A DICTIONARY!
            session["user_id"] = user["id"] #instead of keeping EVERYTHING from that row, we just keep "id"
            #the left side is like the "wristband" telling python who is logged in; the right side
            session["role"] = user["role"] #keeping track of admins/teachers
            return redirect("/") #use redirect for URL that isn't HTML
        else:
            #if NOT found, bring them to the login page again with an error
            return render_template("login.html", error="Inavlid email or password")

    except Exception as e: #if db has any issues, handle here
        print(f"Database error: {e}")
        return render_template("login.html", error="System error, please try again later")

    finally: #always rmb to close conn so nothing (db) locks up!
        db.close()


@app.route("/logout")
def logout():
    session.clear() #using the .clear() function to wipe the session clean
    return render_template("/") #bring them back to "view only"

#I can just call this function inside every editable page
def can_edit(): #making sure students are not typing /admin to access things; for security too!
    return "user_id" in session and session.get("role") in ["teacher", "admin"] 
    #checks their "wristband" and see if they qualify to edit


@app.route("/")
def home():
    home_info = {} #prevents crashing if db is empty
    db = get_db_conn()
    try: 
        cursor = db.cursor()
        rows = cursor.execute("SELECT section, description FROM home where page = 'home'").fetchall()
        #use fetchall bc there are 3 rows now!
        for row in rows: #using for loop to store our rows of info into a dictionary
            #each with a section and description (unique)
            home_info[row["section"]] = row["description"]
    except Exception as e:
        print(f"Oops, error fetching home sections; {e}")
    finally:
        db.close()

    return render_template("home.html", info_box=home_info)


#creating a logging history function so i dont have to repeat the same lines of code everytime
def log_history(db, id, page):
    cursor = db.cursor() #no need to db to get connection, bc this will be called in other routes that should alr be connected to db
    query = """
        INSERT INTO history (updateDatetime, id, page)
        VALUES (CURRENT_TIMESTAMP, ?, ?)
    """
    log = cursor.execute(query, id, page)
    return log 


@app.route("/announcements")
def announcements():
    db = get_db_conn()
    cursor = db.cursor()
    content = cursor.execute("SELECT description FROM announcement").fetchone() #bc theres only 1 row for announcement table, it's updated daily
    if content:
        return render_template("announcements.html", daily_msg=content['description']) #bc its a dict, i must specify the column
    else:
        return render_template("announcements.html", daily_msg="")

    db.close()

@app.route("/update_announcements", methods=["POST"]) #default method is GET, so we must specify it here
def update_announcements():
    #first check if they qualify to edit
    if not can_edit():
        return redirect("/login")

    new_text = request.form.get("new_content") #html page must match this new_content to share the data properly
    editor = session.get("user_id") #get who is editing for the history page
    
    db = get_db_conn()
    cursor = db.cursor()
    query = """
        UPDATE announcement
        SET description = ?, id = ?, updatetime = CURRENT_TIMESTAMP
        """
        #CURRENT_TIMESTAMP is a keyword in SQL that automatically inputs the time
    cursor.execute(query, (new_text, editor)) #dont forget to pass on the variables for ?
    
    #UPDATE, SET requires a commit to save!
    db.commit()
    db.close()

    return redirect("/announcements")


@app.route("/calendar")
def calendar():

    return render_template("calendar.html")

@app.route("/clubs")
def clubs():

    return render_template("clubs.html")

@app.route("/qa", methods=["GET"])
def qa():
    db = get_db_conn()
    cursor = db.cursor()
    #connect to db & fetch all approved questions
    query = """
        SELECT qa_id, q_text, a_text, askedTime, updateDatetime FROM qa WHERE is_visible=1 ORDER BY askedTime DESC
    """
    everything = cursor.execute(query).fetchall()
    db.close()

    return render_template("qa.html", all_qa=everything)


@app.route("/submit_question", methods=["POST"])
def submit_question():
    #connecting to frontend to share the question they posted
    question = request.form.get("question_content")
    
    db = get_db_conn()
    cursor = db.cursor()
    query = """
        INSERT INTO qa (q_text, askedTime, page, is_visible)
        VALUES (?, CURRENT_TIMESTAMP, 'qa', 0)
    """ #in sql, INSERT & VALUES work tgt to create a new record 
    cursor.execute(query, (question))
    db.commit()
    db.close()

    return redirect("/qa")


@app.route("/answer_question", methods=["POST"])
def answer_question():
    if not can_edit():
        return redirect("/login")
    
    question_id = request.form.get('qa_id') #get the question id that identifies each question
    answer = request.form.get("answer_content") #get the answer inputted
    visibility = request.form.get("visibility")
    editor = session.get('user_id') #keep track of who answered it

    db = get_db_conn()
    cursor = db.cursor()
    query = """
        UPDATE qa
        SET a_text = ?, id = ?, updateDatetime = CURRENT_TIMESTAMP, is_visible = ? WHERE qa_id = ?
    """ #now we update those empty columns of "a_text"
    cursor.execute(query, (answer, editor, visibility, question_id))
    db.commit()
    db.close()
    return redirect("/qa")


@app.route("/resources")
def resources():
    db = get_db_conn()
    cursor = db.cursor()
    rows = cursor.execute("SELECT label, url FROM resources").fetchall() #we want all the listed links
    db.close()
    return render_template("resources.html", resource_list=rows)


if __name__ == "__main__":
    app.run(debug=True)