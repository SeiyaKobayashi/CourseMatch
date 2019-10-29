from flask import Flask, g
from config import DATABASE
import sqlite3

app = Flask(__name__)

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('models/user.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_db():
    db = getattr(g, '_database', None)
    if db == None:
        g._database = sqlite3.connect(DATABASE)
        db = g._database
        db.row_factory = sqlite3.Row     # results of queries are of nametuple type
    return db

def modify_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    cur.close()
    return None

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    data = cur.fetchall()
    cur.close()
    return (data[0] if data else None) if one else data

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db != None:
        db.close()
