from flask import Flask, render_template, request, redirect, url_for, session, flash, secrets, string
import sqlite3

app = Flask(__name__)
app.secret_key = "karens_secret_key" #required to use sessions
conn = None

def get_db_conn(): #whenever I need to connect to db, I can just call this function
    conn = sqlite3.connect('database.db') #connect to the db file
    conn.row_factory = sqlite3.Row #row factory allows named access
    return conn

#I can just call this function inside every editable page
def can_edit(): #making sure students are not typing /admin to access things; for security too!
    is_active = session.get("is_active")
    if is_active == 0: #if this account was disabled, they cannot have access
        return False
    return "user_id" in session and session.get("role") in ["teacher", "admin"] 
    #checks their "wristband" and see if they qualify to edit and account is active

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
        if user and user["is_active"] == 1:
            #if teacher is found, save their info in session and direct them to the home page
            #sessions help keep track who is logged in when they navigate through diff pages, ITS A DICTIONARY!
            session["user_id"] = user["id"] #instead of keeping EVERYTHING from that row, we just keep "id"
            #the left side is like the "wristband" telling python who is logged in; the right side
            session["role"] = user["role"] #keeping track of admins/teachers
            session["is_active"] = user["is_active"]
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
    log_history(db, editor, 'announcement') #using the previously made function to update history page's data

    #UPDATE, SET requires a commit to save!
    db.commit()
    db.close()

    return redirect("/announcements") #use redirect here to refresh the page


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
    cursor.execute(query, (question)).fetchall()
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
    cursor.execute(query, (answer, editor, visibility, question_id)).fetchall()
    log_history(db, editor, 'qa')
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


@app.route("/clubs")
def clubs():
    db = get_db_conn()
    cursor = db.cursor()
    query = """
        SELECT club_name, description, image_path, updateDatetime, id FROM clubs ORDER BY updateDatetime DESC
    """
    club_list = cursor.execute(query).fetchall()
    db.close()
    return render_template("clubs.html", club_list=club_list)

@app.route("/update_clubs", methods=["POST"])
def update_clubs():
    if not can_edit():
        return redirect("/login")
        
    edited_id = request.form.get("club_id")
    new_descp = request.form.get("updated_club")
    if not new img:
        new_img = request.form.get("new_img_link")
    editor = session.get('user_id')
    db = get_db_conn()
    cursor = db.cursor()
    query = """
        UPDATE clubs
        SET description = ?, image_path = ?, id = ?, updateDatetime = CURRENT_TIMESTAMP WHERE club_id = ?
    """
    cursor.execute(query, (new_descp, new_img, editor, edited_id))
    log_history(db, editor, 'clubs')
    db.commit()
    db.close()
    return redirect("/clubs")


@app.route("/calendar")
def calendar():
    db = get_db_conn()
    cursor = db.cursor()
    query = """
        SELECT eventdate, description, category FROM calendar ORDER BY eventdate ASC
    """
    all_events = cursor.execute(query).fetchall()
    db.close()
    return render_template("calendar.html", display_events=all_events)

@app.route("/update_calendar", methods=["POST"]) #this is the route where teachers can update calendar
def update_calendar():
    if not can_edit():
        return redirect("/login")
    date = request.form.get("eventdate")
    new_text = request.form.get("description")
    category = request.form.get("category")
    editor = session.get("user_id")

    db = get_db_conn()
    cursor = db.cursor()
    #the next line checks if this day already has info, if so then we just update
    existing = cursor.execute("SELECT 1 FROM calendar WHERE eventdate = ?", (date_id)).fetchone()
    if existing: #means YES, this eventdate has already been inserted and is not empty
        cursor.execute("""
            UPDATE calendar
            SET description = ?, id = ?, category = ?, updateDatetime = CURRENT_TIMESTAMP WHERE eventdate = ?
        """, (new_text, editor, category)
        )
    else: #means NO, this event was empty, first time adding content
        cursor.execute("""
            INSERT INTO calendar (eventdate, description, category, id, updateDatetime)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (date, new_text, category, editor)
        )
    
    log_history(db, editor, 'calendar')
    db.commit()
    db.close()
    return redirect("/calendar")


@app.route("/history")
def history():
    if session.get("role") != "admin": #here we are ensuring that nobody other than admins are allowed to see this page
        return redirect("/login")
    db = get_db_conn()
    cursor = db.cursor()
    all_logs = cursor.execute("""SELECT * FROM history ORDER BY updateDatetime DESC""").fetchall()
    
    db.close()
    return render_template("history.html", display_logs=all_logs)

@app.route("/management")
def management():
    if session.get("role") != "admin": 
        return redirect("/login")
    db = get_db_conn()
    cursor = db.cursor()
    all_accounts = cursor.execute("""SELECT id, email, role, is_active FROM teachers ORDER BY id""").fetchall()
    
    db.close()
    return render_template("management.html", all_accounts=all_accounts)

@app.route("/manage_accounts", methods=["POST"])
def manage_accounts():
    if session.get("role") != "admin": 
        return redirect("/login")
    
    editor = session.get("user_id")
    target_email = request.form.get("target_email") #know which account is being edited
    action = request.form.get("action") #know what action is being done to this account
    db = get_db_conn()
    cursor = db.cursor()
    row = cursor.execute("""SELECT id FROM teachers WHERE email = ? """, (target_email)).fetchone()
    temp_id = row[0] #we fetched the row of data above, but we want numbers

    if action == "disable": #disabling the account
        cursor.execute(""" 
            UPDATE teachers 
            SET is_active = 0 WHERE id = ?
        """, temp_id)

    elif action == "remove": #removing accounts, deletes the whole row, that id is gone forever, and is not replaced
        cursor.execute("""
            DELETE teachers WHERE id = ?
        """, (temp_id))
        db.commit()
        db.close()
        return redirect("/management?deleted=success") 
        #everything after the ? will be sent to html, tell em it was successful!

    elif action == "reset": #resetting password 
        alphabet = string.ascii_letters + string.digits
        new_pass = ''.join(secrets.choice(alphabet) for i in range(8))
        #the two lines above help create a random string that is 8 characters long
        cursor.execute("""
            UPDATE teachers
            SET password = ? WHERE id = ?
        """, new_pass, temp_id)
        db.commit()
        db.close()
        return redirect(f"/management?new_password={new_pass}") 
        #first refresh to the page, the "?" starts a query string to send the data

    else: #this case is when the action is to change role to 'teacher' or 'admin'
        cursor.execute("""
            UPDATE teachers
            SET role = ? WHERE id = ?
        """, (action, temp_id))

    log_history(db, editor, 'manage_accounts')
    db.commit()
    db.close()
    return redirect("/management")







if __name__ == "__main__":
    app.run(debug=True)