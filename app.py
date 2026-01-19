from flask import Flask, render_template, request, redirect, url_for, session, flash 
import secrets
import string
import sqlite3
import calendar
from datetime import datetime #these two imports are for the calendar page
import pytz #we need to this to change to Toronto's time zone

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

def get_canada_time(): #making this a function so we can just call it whenever we had to use CURRENT_TIMESTAMP
    canada_tz = pytz.timezone('America/Toronto')
    return datetime.now(canada_tz).strftime('%Y-%m-%d %H:%M:%S')

#creating a logging history function so i dont have to repeat the same lines of code everytime
def log_history(db, id, page):
    cursor = db.cursor() #no need to db to get connection, bc this will be called in other routes that should alr be connected to db
    time = get_canada_time()

    query = """
        INSERT INTO history (updateDatetime, id, page)
        VALUES (?, ?, ?)
    """
    log = cursor.execute(query, (time, id, page))
    return log 

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET": #the if, try, except, finally are used for error handling so nothing craches :)
        return render_template("login.html")
    email = request.form.get("user_id") or request.form.get("username")
    password = request.form.get("password")
    db = None #initialize to prevent crashing
    try: #connect to the db and check if the user exists
        db = get_db_conn() #get the connection
        cursor = db.cursor() #create a cursor to do the sql handling
        cursor.execute("SELECT * FROM teachers where email=? AND password=?", (email, password))
        user = cursor.fetchone() 
        if user and user["is_active"] == 1:
            #if teacher is found, save their info in session and direct them to the home page
            #sessions help keep track who is logged in when they navigate through diff pages, ITS A DICTIONARY!
            session["user_id"] = user["id"] #instead of keeping EVERYTHING from that row, we just keep "id"
            #the left side is like the "wristband" telling python who is logged in
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
        if db: 
            db.close()


@app.route("/logout")
def logout():
    session.clear() #using the .clear() function to wipe the session clean
    return redirect("/") #bring them back to "view only"


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


@app.route("/announcements")
def announcements():
    today_str = datetime.now(pytz.timezone('America/Toronto')).strftime("%A, %B %d, %Y") #i wanted to display tdy's date
    #A: day of week B:month d:day Y:year
    db = get_db_conn()
    cursor = db.cursor()
    content = cursor.execute("SELECT description FROM announcement").fetchone() #bc theres only 1 row for announcement table, it's updated daily
    if content:
        return render_template("announcements.html", daily_msg=content['description'], today=today_str) #bc its a dict, i must specify the column
    else:
        return render_template("announcements.html", daily_msg="", today=today_str)

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
    time = get_canada_time()
    query = """
        UPDATE announcement
        SET description = ?, id = ?, updateDatetime = ?
        """
    cursor.execute(query, (new_text, editor, time)) #dont forget to pass on the variables for ?
    log_history(db, editor, 'edited announcements') #using the previously made function to update history page's data

    #UPDATE, SET requires a commit to save!
    db.commit()
    db.close()

    return redirect("/announcements") #use redirect here to refresh the page


@app.route("/qa", methods=["GET"])
def qa():
    db = get_db_conn()
    cursor = db.cursor()
    #connect to db & fetch all approved questions
    if session.get('role') in ['admin', 'teacher']: #teachers are allowed to see ALL the questions
        query = "SELECT * FROM qa ORDER BY askedTime DESC"
    else: #viewers are only allowed to see the ones marked visible by teachers
        query = "SELECT * FROM qa WHERE is_visible=1 ORDER BY askedTime DESC"
    
    db.row_factory = sqlite3.Row #to be able to access by column names
    cursor = db.cursor()
    everything = cursor.execute(query).fetchall()
    db.close()

    return render_template("qa.html", questions=everything)


@app.route("/submit_question", methods=["POST"])
def submit_question():
    db = get_db_conn()
    cursor = db.cursor()
    content = request.form.get("question_content")
    asked_time = get_canada_time()
    if not content: 
        return redirect("/qa")
    query = """
        INSERT INTO qa (q_text, askedTime, is_visible)
        VALUES (?, ?, ?)
    """
    cursor.execute(query, (content, asked_time, 0))
    db.commit()
    db.close()
    return redirect("/qa?submitted=true")


@app.route("/answer_question", methods=["POST"])
def answer_question():
    if not can_edit():
        return redirect("/login")
    
    question_id = request.form.get('qa_id') #get the question id that identifies each question
    answer = request.form.get("answer_content") #get the answer inputted
    visibility = 1 if request.form.get("visibility") else 0
    editor = session.get('user_id') #keep track of who answered it

    db = get_db_conn()
    cursor = db.cursor()
    time = get_canada_time()
    query = """
        UPDATE qa
        SET a_text = ?, id = ?, updateDatetime = ?, is_visible = ? WHERE qa_id = ?
    """ #now we update those empty columns of "a_text"
    cursor.execute(query, (answer, editor, time, visibility, question_id))
    log_history(db, editor, 'edited q&a page')
    db.commit()
    db.close()
    return redirect("/qa")

@app.route("/delete_question", methods=["POST"])
def delete_question():
    if not can_edit():
        return redirect("/login")
        
    question_id = request.form.get("question_id")
    editor = session.get('user_id')
    
    db = get_db_conn()
    cursor = db.cursor()
    cursor.execute("DELETE FROM qa WHERE qa_id = ?", (question_id,))
    log_history(db, editor, "deleted a question")
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
        SELECT club_name, description, image_path, club_id FROM clubs ORDER BY updateDatetime DESC
    """
    club_list = cursor.execute(query).fetchall()
    db.close()
    return render_template("clubs.html", club_list=club_list)

@app.route("/update_clubs", methods=["POST"])
def update_clubs():
    if not can_edit():
        return redirect("/login")
        
    edited_id = request.form.get("club_id")
    new_name = request.form.get("updated_name")
    new_descp = request.form.get("updated_club")
    new_img = request.form.get("new_img_link")    
    editor = session.get('user_id')
    time = get_canada_time()
    db = get_db_conn()
    cursor = db.cursor()
    current = cursor.execute("SELECT club_name, image_path FROM clubs WHERE club_id = ?", (edited_id,)).fetchone()
    if not new_name and current: #just use the old name from db if not given a new name
        new_name = current["club_name"]
    if not new_img: 
        if current and current["image_path"]:
            new_img = current["image_path"] # Keep old image if it exists
        else:
            new_img = "" # Force empty string instead of None
    query = """
        UPDATE clubs
        SET club_name = ?, description = ?, image_path = ?, id = ?, updateDatetime = ? WHERE club_id = ?
    """
    cursor.execute(query, (new_name, new_descp, new_img, editor, time, edited_id))
    log_history(db, editor, 'edited clubs page')
    db.commit()
    db.close()
    return redirect("/clubs")

@app.route("/add_clubs", methods=["POST"])
def add_clubs():
    if not can_edit():
        return redirect("/login")
    club_name = request.form.get("club_name")
    description = request.form.get("description")
    img = request.form.get("img_link")
    editor = session.get('user_id')
    time = get_canada_time()
    if not img or img=="None":
        img = ""
    db = get_db_conn()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO clubs (club_name, image_path, description, updateDatetime, id, page)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (club_name, img, description, time, editor, 'clubs'))
    log_history(db, editor, "added new club")
    db.commit()
    db.close()
    return redirect("/clubs")

@app.route("/delete_club", methods=["POST"])
def delete_club():
    if not can_edit():
        return redirect("/login")
        
    club_id = request.form.get("club_id")
    club_name = request.form.get("club_name") # Sent for the history log
    editor = session.get('user_id')
    
    db = get_db_conn()
    cursor = db.cursor()
    cursor.execute("""DELETE FROM clubs WHERE club_id = ?""", (club_id,))
    log_history(db, editor, f"removed club: {club_name}")
    db.commit()
    db.close()
    return redirect("/clubs")

@app.route("/calendar")
def calendar_view():
    canada_tz = pytz.timezone('America/Toronto') #changing time zone
    now = datetime.now(canada_tz)
    if now.month >= 8:
        start_year = now.year
    else:
        start_year = now.year - 1
    #first get the current month 
    month = int(request.args.get('month', now.month))
    year = int(request.args.get('year', now.year))
    today_str = now.strftime("%Y-%m-%d") #get tdy's date to colour code it in the calendar.html
    #now restrict them: allows only Sept to June
    if year < start_year or (year == start_year and month < 9):
        month, year = 9, start_year
    elif year > start_year + 1 or (year == start_year + 1 and month > 6):
        month, year = 6, start_year + 1
    db = get_db_conn()
    cursor = db.cursor()
    #so we are only fetching the current month's data
    date_filter = f"{year}-{month:02d}-%"
    rows = cursor.execute("SELECT eventdate, description, category, notes FROM calendar WHERE eventdate LIKE ?", (date_filter,)).fetchall()
    clean_events = [list(row) for row in rows] #converting to a list of lists to prevent tojson from crashing
    calendar.setfirstweekday(calendar.SUNDAY)
    grid = calendar.monthcalendar(year, month) #build the calendar grid
    month_name = calendar.month_name[month]
    db.close()
    return render_template("calendar.html", 
                           display_events=clean_events, 
                           grid=grid, 
                           month_name=month_name, 
                           month=month, year=year,
                           sy_start=start_year,
                           today=today_str)

@app.route("/update_calendar", methods=["POST"]) #this is the route where teachers can update calendar
def update_calendar():
    if not can_edit():
        return redirect("/login")
    canada_tz = pytz.timezone('America/Toronto')
    now_canada = datetime.now(canada_tz).strftime('%Y-%m-%d %H:%M:%S')
    date = request.form.get("eventdate")
    new_text = request.form.get("description", "")
    category = request.form.get("category") or "regular"
    editor = session.get("user_id")
    notes = request.form.get("notes", "")
    try: 
        db = get_db_conn()
        cursor = db.cursor()
        #the next line checks if this day already has info, if so then we just update
        existing = cursor.execute("SELECT 1 FROM calendar WHERE eventdate = ?", (date,)).fetchone()
        if existing: #means YES, this eventdate has already been inserted and is not empty
            cursor.execute("""
                UPDATE calendar
                SET description = ?, id = ?, category = ?, notes = ?, page = ?, updateDatetime = ? WHERE eventdate = ?
            """, (new_text, editor, category, notes, "calendar", now_canada, date)
            )
        else: #means NO, this event was empty, first time adding content
            cursor.execute("""
                INSERT INTO calendar (eventdate, description, notes, category, id, page, updateDatetime)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (date, new_text, notes, category, editor, "calendar", now_canada)
            )
        
        log_history(db, editor, 'edited calendar page')
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
        if db:
            db.rollback() #undo changes if it failed
    finally:
        if db:
            db.close() #closes no matter what

    return redirect(f"/calendar?month={date[5:7]}&year={date[0:4]}")


@app.route("/history")
def history():
    if session.get("role") != "admin": #here we are ensuring that nobody other than admins are allowed to see this page
        return redirect("/login")
    db = get_db_conn()
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    query = """
        SELECT teachers.email, history.updateDatetime, history.page FROM history
        JOIN teachers ON history.id = teachers.id
        ORDER BY history.updateDatetime DESC
    """
    #the JOIN is a sql command that allows connectin btw two tables that share the same column
    all_logs = cursor.execute(query).fetchall()
    db.close()
    return render_template("history.html", display_logs=all_logs)

@app.route("/clear_history", methods=["POST"])
def clear_history():
    if session.get("role") != "admin": 
        return redirect("/login")
    db = get_db_conn()
    cursor = db.cursor()
    try:
        cursor.execute("""DELETE FROM history """)
        cursor.execute("""DELETE FROM sqlite_sequence WHERE name='history'""")
        db.commit()
    except Exception as e:
        print(f'Error clearing history table')
    finally:
        db.close()
    return redirect("/history")



@app.route("/management")
def management():
    if session.get("role") != "admin": 
        return redirect("/login")
    db = get_db_conn()
    db.row_factory = sqlite3.Row
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
    row = cursor.execute("""SELECT id FROM teachers WHERE email = ? """, (target_email,)).fetchone()

    if action == "disable": #disabling the account
        cursor.execute(""" 
            UPDATE teachers 
            SET is_active = 0 WHERE email = ?
        """, (target_email,))

    elif action == "remove": #removing accounts, deletes the whole row, that id is gone forever, and is not replaced
        cursor.execute("""
            DELETE FROM teachers WHERE email = ?
        """, (target_email,))
        log_history(db, editor, 'removed an account')
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
            SET password = ? WHERE email = ?
        """, (new_pass, target_email,))
        log_history(db, editor, 'reset a password')
        db.commit()
        db.close()
        return redirect(f"/management?new_password={new_pass}") 
        #first refresh to the page, the "?" starts a query string to send the data

    elif action == "set_teacher": 
        #this case is when the action is to change role to 'teacher' or 'admin'
        cursor.execute("""
            UPDATE teachers
            SET role = "teacher", is_active = 1 WHERE email = ?
        """, (target_email,))
        log_history(db, editor, 'changed role to teacher')
    elif action == "set_admin":
        cursor.execute("""
            UPDATE teachers
            SET role = "admin", is_active = 1 WHERE email = ?
        """, (target_email,))
        log_history(db, editor, 'changed role to admin')

    if db: #could lead to errors since for 'remove' and 'reset' the db is alr closed, so we check here
        db.commit()
        db.close()
    return redirect("/management")

@app.route("/add_account", methods=["POST"])
def add_account():
    if session.get("role") != "admin": 
        return redirect("/login")
    
    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role")
    editor = session.get("user_id")
    
    db = get_db_conn()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO teachers (email, password, role, is_active) 
            VALUES (?, ?, ?, 1)
        """, (email, password, role))
        log_history(db, editor, 'added an account')
        db.commit()
    except Exception as e:
        #if theres an error while trying to add
        print(f"Error: {e}") 
    finally:
        db.close()
        
    return redirect("/management")



if __name__ == "__main__":
    app.run(debug=True)