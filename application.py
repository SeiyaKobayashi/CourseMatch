from flask import request, render_template, redirect, url_for, session, flash
from init_db import app, init_db, get_db, modify_db, query_db
from config import SECRET_KEY, emailRegEx, pwRegEx
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
            return render_template("register.html", session=session)
        elif request.method == 'POST':
            # Store inputs (except password) in session to auto-fill the forms when redirected
            session['name']   = request.form.get("name")
            session['email']  = request.form.get("email")
            session['school'] = request.form.get("school")
            session['gender'] = request.form.get("gender") \
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
            modify_db('user', "INSERT INTO user (name, email, password, gender, school, year, major, minor, courses) \
                       VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (session['name'], session['email'], request.form.get("password"), session['gender'],
                       session['school'], 'N/A', 'N/A', 'N/A', 'N/A'))

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
            user = query_db('user', "SELECT * FROM user WHERE id = ?", (session["userid"],), True)
            return render_template("edit_profile.html", session=session, user=user)
        elif request.method == 'POST':
            # Avoid storing in session (might confuse users)
            name    = request.form.get("name")
            email   = request.form.get("email")
            school  = request.form.get("school")
            gender  = request.form.get("gender") \
                      if (request.form.get("gender") and request.form.get("gender") != 'PNTA') \
                      else 'N/A'
            year    = request.form.get("year") if request.form.get("year") else 'N/A'
            major   = request.form.get("major") if request.form.get("major") else 'N/A'
            minor   = request.form.get("minor") if request.form.get("minor") else 'N/A'
            courses = request.form.get("courses") if request.form.get("courses") else 'N/A'

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
                       SET name=?, email=?, password=?, gender=?, school=?, year=?, major=?, minor=?, courses=?\
                       WHERE id=?",
                       (name, email, request.form.get("password"), gender,
                        school, year, major, minor, courses, userid))

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

# Function to be run before app starts running
@app.before_first_request
def init_app():
    if not path.exists("models/user.db"):
        init_db("user")

    if not path.exists("models/college.db"):
        init_db("college")
        modify_db('college', "INSERT INTO college (college) VALUES(?)", ('BU',))

    if not path.exists("models/school.db"):
        init_db("school")
        schools = scrapeSchools()
        for i in range(len(schools)):
            modify_db('school', "INSERT INTO school (id, college_id, school) VALUES(?, ?, ?)",
                     (i+1, query_db('college', "SELECT * FROM college WHERE college=?", ('BU',), True)['id'], schools[i]))

    if not path.exists("models/department.db"):
        init_db("department")
        departments = scrapeDepartments()
        for i in range(len(departments)):
            modify_db('department', "INSERT INTO department (id, college_id, school_id, department, link) VALUES(?, ?, ?, ?, ?)",
                     (i+1,
                      query_db('college', "SELECT * FROM college WHERE college=?", ('BU',), True)['id'],
                      query_db('school', "SELECT * FROM school WHERE school=?", ('College of Arts & Sciences',), True)['id'],
                      departments[i]['department'],
                      departments[i]['link']))

    if not path.exists("models/course.db"):
        init_db("course")
        id = 1
        for department in query_db('department', "SELECT * FROM department"):
            courses = scrapeCourses(department['link'])
            for i in range(len(courses)):
                modify_db('course', "INSERT INTO course (id, college_id, school_id, department_id, course, link, description) \
                           VALUES(?, ?, ?, ?, ?, ?, ?)",
                          (id,
                           query_db('college', "SELECT * FROM college WHERE college=?", ('BU',), True)['id'],
                           query_db('school', "SELECT * FROM school WHERE school=?", ('College of Arts & Sciences',), True)['id'],
                           query_db('department', "SELECT * FROM department WHERE department=?",
                                   (department['department'],), True)['id'],
                           courses[i]['course'],
                           courses[i]['link'],
                           'N/A'
                           ))
                id += 1

def scrapeSchools(URL='https://www.bu.edu/academics/schools-colleges/'):
    soup = BeautifulSoup(requests.get(URL).text, "html.parser")
    rawData = soup.select('.school')
    schoolsData = []

    for i in range(len(rawData)):
        schoolsData.append(rawData[i].find('h3').text)

    return schoolsData

# Scrapes list of departments (name + link) from top page
def scrapeDepartments(URL='https://www.bu.edu/academics/cas/courses/'):
    soup = BeautifulSoup(requests.get(URL).text, "html.parser")
    rawData = soup.select('.level_2')
    departmentsData = {}

    for i in range(len(rawData)):
        departmentsData[i] = {'department': rawData[i].contents[0],
                              'link': rawData[i]['href']}

    return departmentsData

def scrapeCourses(departmentURL):
    soup_all = BeautifulSoup(requests.get(departmentURL).text, "html.parser")
    if soup_all.find('div', {'class': 'pagination'}) == None:
        numOfPages = 1
    else:
        numOfPages = len(soup_all.find('div', {'class': 'pagination'}).find_all('a')) + 1
    rawData = []
    coursesData = []

    for i in range(numOfPages):
        if i == 0:
            soup = BeautifulSoup(requests.get(departmentURL).text, "html.parser")
        else:
            soup = BeautifulSoup(requests.get(departmentURL+str(i+1)+'/').text, "html.parser")
        rawData.extend(soup.find('ul', {'class': 'course-feed'}).find_all('li', {'class': None}))

    for j in range(len(rawData)):
        coursesData.append({'course': rawData[j].find('a').text,
                            'link': 'https://www.bu.edu' + rawData[j].find('a')['href']})

    return coursesData

if __name__ == '__main__':
    app.secret_key = SECRET_KEY
    app.run()
