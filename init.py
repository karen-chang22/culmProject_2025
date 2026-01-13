import sqlite3
connection = sqlite3.connect("database.db")
cursor = connection.cursor()

#TEACHER TABLE
cursor.execute('''
    CREATE TABLE IF NOT EXISTS teachers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT UNIQUE NOT NULL,
    role TEXT CHECK (role IN ('admin', 'teacher', 'disabled')) DEFAULT 'none', 
    is_active BOOLEAN DEFAULT 1
    ); 
''')

#HOME TABLE 
cursor.execute ('''
    CREATE TABLE IF NOT EXISTS home(
    section TEXT NOT NULL,
    description TEXT NOT NULL,
    updateDatetime TEXT,
    id INTEGER,
    page TEXT NOT NULL,
    FOREIGN KEY(id) REFERENCES teachers(id)
    );
''')
cursor.execute ('''
    INSERT INTO home
    (page, section, description)
    VALUES 
    ('home', 'contact', 'Address: 11 Spring Farm Road, Aurora, ON L4G 7W2\nEmail: dr.g.w.williams.ss@yrdsb.ca\nPhone: (905) 727-3131'),
    ('home', 'hours', 'Bell Times: 8:20 AM - 3:00 PM'),
    ('home', 'map', 'images/school_pic.png');
''')

#CLUB TABLE
cursor.execute ('''
    CREATE TABLE IF NOT EXISTS clubs(
    club_id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    image_path TEXT,
    updateDatetime TEXT,
    id INTEGER,
    page TEXT NOT NULL,
    FOREIGN KEY(id) REFERENCES teachers(id)
    );
''') 
cursor.execute ('''
    INSERT INTO clubs
    (page)
    VALUES 
    ('clubs');
''')

#CALENDAR TABLE
cursor.execute ('''
    CREATE TABLE IF NOT EXISTS calendar(
    eventdate TEXT PRIMARY KEY,
    description TEXT,
    updateDatetime TEXT,
    id INTEGER,
    category TEXT CHECK (category in ('holiday', 'snowday', 'regular')),
    page TEXT NOT NULL,
    FOREIGN KEY(id) REFERENCES teachers(id)
    );
''') 
cursor.execute ('''
    INSERT INTO calendar
    (page)
    VALUES 
    ('calendar');
''')

#ANNOUNCEMENT TABLE
cursor.execute ('''
    CREATE TABLE IF NOT EXISTS announcement(
    description TEXT,
    updateDatetime TEXT, 
    id INTEGER,
    page TEXT NOT NULL,
    FOREIGN KEY(id) REFERENCES teachers(id)
    );
''')
cursor.execute ('''
    INSERT INTO announcement
    (page)
    VALUES 
    ('announcement');
''')

#QA TABLE
cursor.execute ('''
    CREATE TABLE IF NOT EXISTS qa(
    qa_id INTEGER PRIMARY KEY AUTOINCREMENT,
    q_text TEXT,
    a_text TEXT DEFAULT "Waiting for a response...",
    askedTime TEXT,
    updateDatetime TEXT,
    id INTEGER,
    is_visible BOOLEAN,
    page TEXT,
    FOREIGN KEY(id) REFERENCES teachers(id)
    );
''')

#RESOURCES TABLE
cursor.execute ('''
    CREATE TABLE IF NOT EXISTS resources(
    resources_id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    url TEXT NOT NULL,
    page TEXT NOT NULL
    );
''')
cursor.execute ('''
    INSERT INTO resources (label, url, page)
    VALUES 
    ('Teach Assist', 'https://ta.yrdsb.ca/yrdsb/', 'resources'),
    ('CorsCal', 'https://www.corscal.com/', 'resources'),
    ('School Cash Online', 'https://www2.yrdsb.ca/node/1426', 'resources'),
    ('YRDSB', 'https://www2.yrdsb.ca/', 'resources'),
    ('Report It', 'https://www2.yrdsb.ca/student-support/caring-and-safe-schools/report-it', 'resources'),
    ('Kids Help Phone', 'https://kidshelpphone.ca/', 'resources');
''')

#HISTORY TABLE
cursor.execute ('''
    CREATE TABLE IF NOT EXISTS history(
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    updateDatetime TEXT,
    id INTEGER,
    page TEXT NOT NULL,
    FOREIGN KEY(id) REFERENCES teachers(id)
    ); 
''')
cursor.execute ('''
    INSERT INTO history
    (page)
    VALUES 
    ('history');
''')

connection.commit()
connection.close()