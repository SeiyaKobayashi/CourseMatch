from flask import request, render_template, redirect, url_for, session, flash
from init_db import app, init_db, get_db, modify_db, query_db
from config import SECRET_KEY, emailRegEx, pwRegEx
from scraping import scrapeSchools, scrapeDepartments, scrapeCourses
from os import path
from bs4 import BeautifulSoup
import re
import requests

# Top page
@app.route("/")
def top():
    return render_template("top.html")

# Register (Sign-Up) page
@app.route("/register", methods=["GET", "POST"])
def register():
    # If already logged in
    if 'userid' in session:
        flash(u"You're already logged in. Redirected to your profile page.", 'warning')
        return redirect(url_for('profile', userid=session['userid']))
    else:
        if request.method == 'GET':
            colleges = query_db('college', "SELECT * FROM college")
            return render_template("register.html", session=session, colleges=colleges)
        elif request.method == 'POST':
            # Store inputs (except password) in session to auto-fill the forms when redirected
            session['name']    = request.form.get("name")
            session['email']   = request.form.get("email")
            session['college'] = request.form.get("college")
            session['gender']  = request.form.get("gender") \
                                 if (request.form.get("gender") and request.form.get("gender") != 'PNTA') \
                                 else 'N/A'

            # Validate email (has to be unique, and has to contain @, followed by .)
            if re.fullmatch(emailRegEx, session['email']) == None:
                flash(u"Invalid email address. Please try again.", 'warning')
                return redirect(url_for("register"))
            elif query_db('user', "SELECT * FROM user WHERE email = ?", (session['email'],), True) != None:
                flash(u"Entered email address is already taken. Please try again with other email address.", 'warning')
                return redirect(url_for("register"))

            # Validate password (has to be longer than 8 characters,
            # and has to contain at least one uppercase, lowercase, and digit, respectively)
            # Also, password is NOT stored in session for security purposes
            if re.fullmatch(pwRegEx, request.form.get("password")) == None:
                flash(u"Invalid password. Password has to be longer than or equal to 8 characters, \
                       and has to contain at least one uppercase, lowercase, and digit.", 'warning')
                return redirect(url_for("register"))
            elif request.form.get("password") != request.form.get("passwordconfirmation"):
                flash(u"Passwords don't match. Please make sure to input the same valid password twice.", 'warning')
                return redirect(url_for("register"))

            # Store new user in DB only if passed all validations
            modify_db('user', "INSERT INTO user (name, email, password, gender, college, school, year, major, minor, profile) \
                       VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (session['name'], session['email'], request.form.get("password"), session['gender'],
                       session['college'], 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'))

            # Store user ID in session just for convenience
            user = query_db('user', "SELECT * FROM user WHERE email = ?", (session['email'],), True)
            session['userid'] = user['id']

            flash(u"Signed up successfully.", 'info')
            return redirect(url_for('profile', userid=session['userid']))

# Log-In (Sign-In) page
@app.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in
    if 'userid' in session:
        flash(u"You're already logged in. Redirected to your profile page.", 'warning')
        return redirect(url_for('profile', userid=session['userid']))
    else:
        if request.method == 'GET':
            return render_template("login.html", session=session)
        elif request.method == 'POST':
            # Store inputs (except password) in session to auto-fill the forms when redirected
            session['email'] = request.form.get("email")

            # Confirm user exists, and entered password matches the stored password
            user = query_db('user', "SELECT * FROM user WHERE email = ?", (session['email'],), True)
            if user == None:
                flash(u"Invalid email or password. Please try again.", 'warning')
                return redirect(url_for("login"))
            elif request.form.get("password") != user['password']:
                flash(u"Invalid email or password. Please try again.", 'warning')
                return redirect(url_for("login"))

            # Store user ID in session just for convenience
            session['userid'] = user['id']

            flash(u"Logged in successfully.", 'info')
            return redirect(url_for('profile', userid=session['userid']))

# Log-Out page
@app.route("/logout")
def logout():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        session.clear()
        flash(u"Logged out successfully. See you again!", 'info')
        return redirect(url_for('top'))

# Account deletion page
@app.route("/<int:userid>/delete", methods=["GET", "POST"])
def delete(userid):
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    # Check if it's a valid user
    elif int(userid) != session['userid']:
        flash(u"You cannot detele other users' accounts. Redirected to your profile page.", 'warning')
        return redirect(url_for('profile', userid=session['userid']))
    else:
        if request.method == 'GET':
            flash(u"You're not allowed to access this page by directly typing URL.", 'warning')
            return redirect(url_for('profile', userid=session['userid']))
        elif request.method == 'POST':
            # Delete user from DB
            modify_db('user', "DELETE FROM user WHERE id = ?", (session['userid'],))
            session.clear()
            flash(u"Your account has been deleted. We hope you come back again...", 'info')
            return redirect(url_for('top'))

# User profile page
@app.route("/<int:userid>")
def profile(userid):
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    # Check if it's a valid user
    user = query_db('user', "SELECT * FROM user WHERE id = ?", (int(userid),), True)
    if user == None:
        flash(u"User doesn't exist. Redirected to your profile page.", 'warning')
        return redirect(url_for('profile', userid=session['userid']))
    elif user['id'] != session['userid']:
        return render_template("profile.html", user=user, editable=False)
    else:
        return render_template("profile.html", user=user, editable=True)

# Profile update page
@app.route("/<int:userid>/edit", methods=["GET", "POST"])
def update(userid):
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    # Check if it's a valid user
    elif int(userid) != session['userid']:
        flash(u"You cannot edit other users' profile. Redirected to your profile page.", 'warning')
        return redirect(url_for('profile', userid=session['userid']))
    else:
        if request.method == 'GET':
            user        = query_db('user', "SELECT * FROM user WHERE id = ?", (session["userid"],), True)
            colleges    = query_db('college', "SELECT * FROM college")
            schools     = query_db('school', "SELECT * FROM school WHERE college_id=?",
                                   ((query_db('college', "SELECT * FROM college WHERE college=?", (user['college'],), True))['id'],))
            departments = query_db('department', "SELECT * FROM department WHERE college_id=?",
                                   ((query_db('college', "SELECT * FROM college WHERE college=?", (user['college'],), True))['id'],))
            return render_template("edit_profile.html",
                                    session=session,
                                    user=user,
                                    colleges=colleges,
                                    schools=schools,
                                    departments=departments)
        elif request.method == 'POST':
            # Avoid storing in session (might confuse users)
            name    = request.form.get("name")
            email   = request.form.get("email")
            college = request.form.get("college")
            school  = request.form.get("school") \
                      if request.form.get("school") and request.form.get("school") != 'N/A' \
                      else 'N/A'
            gender  = request.form.get("gender") \
                      if (request.form.get("gender") and request.form.get("gender") != 'PNTA') \
                      else 'N/A'
            year    = request.form.get("year") if request.form.get("year") else 'N/A'
            major   = request.form.get("major") \
                      if request.form.get("major") and request.form.get("major") != 'N/A' \
                      else 'N/A'
            minor   = request.form.get("minor") \
                      if request.form.get("minor") and request.form.get("minor") != 'N/A' \
                      else 'N/A'
            profile = request.form.get("profile") if request.form.get("profile") else 'N/A'

            # Validate email (has to be unique, and has to contain @, followed by .)
            if re.fullmatch(emailRegEx, request.form.get("email")) == None:
                flash(u"Invalid email address. Please try again.", 'warning')
                return redirect(url_for("update", userid=session['userid']))
            else:
                user = query_db('user', "SELECT * FROM user WHERE email = ?", (request.form.get("email"),), True)
                if (user != None) and (user['id'] != session['userid']):
                    flash(u"Entered email address is already taken. Please try again with other email address.", 'warning')
                    return redirect(url_for("update", userid=session['userid']))

            # Validate password (has to match password in DB)
            if (request.form.get("password") != user['password']):
                flash(u"Invalid password. Please try again.", 'warning')
                return redirect(url_for("update", userid=session['userid']))

            # Update user info in DB only if passed all validations
            modify_db('user', "UPDATE user \
                       SET name=?, email=?, password=?, gender=?, college=?, school=?, year=?, major=?, minor=?, profile=?\
                       WHERE id=?",
                       (name, email, request.form.get("password"), gender,
                        college, school, year, major, minor, profile, userid))

            flash(u"Your profile has been updated successfully.", 'info')
            return redirect(url_for('profile', userid=session['userid']))

# Password change page
@app.route("/<int:userid>/pwupdate", methods=["GET", "POST"])
def change_password(userid):
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    # Check if it's a valid user
    elif int(userid) != session['userid']:
        flash(u"You cannot change other users' password. Redirected to your profile page.", 'warning')
        return redirect(url_for('profile', userid=session['userid']))
    else:
        if request.method == 'GET':
            return render_template("change_password.html", session=session)
        elif request.method == 'POST':
            # Validate password (has to be longer than 8 characters,
            # and has to contain at least one uppercase, lowercase, and digit, respectively)
            # Also, password is NOT stored in session for security purposes
            if re.fullmatch(pwRegEx, request.form.get("password")) == None:
                flash(u"Invalid password. Password has to be longer than or equal to 8 characters, \
                       and has to contain at least one uppercase, lowercase, and digit.", 'warning')
                return redirect(url_for("change_password", userid=session['userid']))
            elif request.form.get("password") != request.form.get("passwordconfirmation"):
                flash(u"Passwords don't match. Please make sure to input the same valid password twice.", 'warning')
                return redirect(url_for("change_password", userid=session['userid']))

            # Update password in DB only if passed all validations
            modify_db('user', "UPDATE user SET password=? WHERE id=?", (request.form.get("password"), session['userid']))

            flash(u"Your password has been updated successfully.", 'info')
            return redirect(url_for('profile', userid=session['userid']))

# User index page
@app.route("/users")
def index_users():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        users = query_db('user', "SELECT * FROM user")
        return render_template("index_users.html", users=users)

# College index page
@app.route("/colleges")
def index_colleges():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        colleges = query_db('college', "SELECT * FROM college")
        collegesWithStats = [(college, len(query_db('school', "SELECT * FROM school WHERE college_id=?", (college['id'],))))
                            if query_db('school', "SELECT * FROM school WHERE college_id=?", (college['id'],))
                            else (college, 0)
                            for college in colleges]
        return render_template("index_colleges.html", colleges=collegesWithStats)

# School index page
@app.route("/schools/")
def index_schools():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        schools = query_db('school', "SELECT * FROM school WHERE college_id=?", (request.args.get('collegeid', 1),))
        schoolsWithStats = [(school, len(query_db('department', "SELECT * FROM department WHERE college_id=? AND school_id=?",
                            (request.args.get('collegeid', 1), school['id']))))
                            if query_db('department', "SELECT * FROM department WHERE college_id=? AND school_id=?",
                            (request.args.get('collegeid', 1), school['id']))
                            else (school, 0)
                            for school in schools]
        return render_template("index_schools.html", schools=schoolsWithStats)

# Department index page
@app.route("/departments/")
def index_departments():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        departments = query_db('department', "SELECT * FROM department WHERE college_id=? AND school_id=?",
                               (request.args.get('collegeid', 1), request.args.get('schoolid', 1)))
        departmentsWithStats = [(department, len(query_db('course', "SELECT * FROM course \
                                WHERE college_id = ? AND school_id=? AND department_id=? ",
                                (request.args.get('collegeid', 1), request.args.get('schoolid', 1), department['id']))))
                                if query_db('course', "SELECT * FROM course \
                                   WHERE college_id = ? AND school_id=? AND department_id=? ",
                                   (request.args.get('collegeid', 1), request.args.get('schoolid', 1), department['id']))
                                else (department, 0)
                                for department in departments]
        return render_template("index_departments.html", departments=departmentsWithStats)

# Course index page
@app.route("/courses/")
def index_courses():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        courses = query_db('course', "SELECT * FROM course WHERE college_id=? AND school_id=? AND department_id=?",
                           (request.args.get('collegeid', 1), request.args.get('schoolid', 1), request.args.get('departmentid', 1)))
        return render_template("index_courses.html", courses=courses)

# Course description page
@app.route("/course/")
def viewCourse():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        course = query_db('course', "SELECT * FROM course WHERE college_id=? AND school_id=? AND department_id=? AND id=?",
                         (request.args.get('collegeid', 1), request.args.get('schoolid', 1),
                          request.args.get('departmentid', 1), request.args.get('courseid', 1)), True)
        return render_template("course_profile.html", course=course)

# Function to be run before app starts running
@app.before_first_request
def init_app():
    if not path.exists("models/user.db"):
        init_db("user")

    if not path.exists("models/college.db"):
        init_db("college")
        # should be modified later
        modify_db('college', "INSERT INTO college (college, link) VALUES(?, ?)",
                  ('BU', 'https://www.bu.edu/academics/schools-colleges/'))

    if not path.exists("models/school.db"):
        init_db("school")
        colleges = query_db('college', "SELECT * FROM college")
        for college in colleges:
            schools = scrapeSchools(college['link'])
            for i in range(len(schools)):
                modify_db('school', "INSERT INTO school (id, college_id, school, link) VALUES(?, ?, ?, ?)",
                          (i+1, college['id'], schools[i]['school'], schools[i]['link']))

    if not path.exists("models/department.db"):
        init_db("department")
        colleges = query_db('college', "SELECT * FROM college")
        for college in colleges:
            schools = query_db('school', "SELECT * FROM school WHERE college_id=?", (college['id'],))
            for school in schools:
                departments = scrapeDepartments(school['link'])
                for i in range(len(departments)):
                    modify_db('department', "INSERT INTO department (id, college_id, school_id, department, link) VALUES(?, ?, ?, ?, ?)",
                              (i+1, college['id'], school['id'], departments[i]['department'], departments[i]['link']))

    if not path.exists("models/course.db"):
        init_db("course")
        colleges = query_db('college', "SELECT * FROM college")
        for college in colleges:
            schools = query_db('school', "SELECT * FROM school WHERE college_id=?", (college['id'],))
            for school in schools:
                departments = query_db('department', "SELECT * FROM department WHERE college_id=? AND school_id=?",
                                       (college['id'], school['id']))
                for department in departments:
                    courses = scrapeCourses(department['link'])
                    for i in range(len(courses)):
                        modify_db('course', "INSERT INTO course (id, college_id, school_id, department_id, course, link, description) \
                                  VALUES(?, ?, ?, ?, ?, ?, ?)",
                                  (i+1, college['id'], school['id'], department['id'],
                                  courses[i]['course'], courses[i]['link'], 'N/A'))

if __name__ == '__main__':
    app.secret_key = SECRET_KEY
    app.run()
