from flask import request, render_template, redirect, url_for, session, flash
from flask_socketio import send, emit, join_room, leave_room
from werkzeug import secure_filename
from init_db import app, socketio, get_db, modify_db, query_db
from config import SECRET_KEY, emailRegEx, pwRegEx
import re
import json
import datetime

# Top page
@app.route("/")
def top():
    if 'courseSearch' in session:
        session.pop('courseSearch', None)
    return render_template("top.html")

# Register (Sign-Up) page
@app.route("/register/", methods=["GET", "POST"])
def register():
    # If already logged in
    if 'userid' in session:
        flash(u"You're already logged in. Redirected to your profile page.", 'warning')
        return redirect(url_for('profile', userid=session['userid']))
    else:
        if request.method == 'GET':
            colleges = query_db('college', "SELECT * FROM college")
            return render_template("register.html", colleges=colleges)
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

            # College must be selected at the time of registration
            if session['college'] == None:
                flash(u"Please select your college.", 'warning')
                return redirect(url_for("register"))

            # Store new user in DB only if passed all validations
            modify_db('user',
                      "INSERT INTO user (name, email, password, gender, college, school, year, \
                      major_1, major_2, minor_1, minor_2, profile, is_on_campus, image) \
                      VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (session['name'], session['email'], request.form.get("password"), session['gender'],
                       int(session['college']), None, None, None, None, None, None, None, 0, 'profile_default.png'))

            # Store user ID in session just for convenience
            user = query_db('user', "SELECT * FROM user WHERE email = ?", (session['email'],), True)
            session['userid'] = user['id']

            # Clear session to avoid related bugs
            session.pop('name', None)
            session.pop('email', None)
            session.pop('college', None)
            session.pop('gender', None)

            flash(u"Signed up successfully.", 'info')
            return redirect(url_for('profile', userid=session['userid']))

# Log-In (Sign-In) page
@app.route("/login/", methods=["GET", "POST"])
def login():
    # If already logged in
    if 'userid' in session:
        flash(u"You're already logged in. Redirected to your profile page.", 'warning')
        return redirect(url_for('profile', userid=session['userid']))
    else:
        if request.method == 'GET':
            return render_template("login.html")
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

            # Clear session to avoid related bugs
            session.pop('email', None)

            # Store user ID in session just for convenience
            session['userid'] = user['id']

            flash(u"Logged in successfully.", 'info')
            return redirect(url_for('profile', userid=session['userid']))

# Log-Out page
@app.route("/logout/")
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
@app.route("/<int:userid>/delete/", methods=["GET", "POST"])
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
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
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
@app.route("/<int:userid>/")
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
    else:
        if 'courseSearch' in session:
            session.pop('courseSearch', None)

        image = '/static/images/' + query_db('user', "SELECT * FROM User WHERE id = ?", (userid,), True)['image']
        is_on_campus = True if (query_db('user', "SELECT * FROM User WHERE id = ?", (userid,), True)['is_on_campus'] == 1) else False
        following = True if query_db('follower', "SELECT * FROM Follower WHERE user_id = ? AND following_user_id = ?",
                                    (session['userid'], userid), True) else False
        followingUsers = query_db('follower', "SELECT * FROM Follower WHERE user_id = ?", (userid,))
        followed  = True if query_db('follower', "SELECT * FROM Follower WHERE user_id = ? AND following_user_id = ?",
                                    (userid, session['userid']), True) else False
        followers = query_db('follower', "SELECT * FROM Follower WHERE following_user_id = ?", (userid,))
        college = query_db('college', "SELECT * FROM college WHERE id = ?", (user['college'],), True)
        school  = query_db('school', "SELECT * FROM school WHERE id = ?", (user['school'],), True) if user['school'] != None else None
        major_1 = query_db('department', "SELECT * FROM department WHERE id = ?", (user['major_1'],), True) if user['major_1'] != None else None
        major_2 = query_db('department', "SELECT * FROM department WHERE id = ?", (user['major_2'],), True) if user['major_2'] != None else None
        minor_1 = query_db('department', "SELECT * FROM department WHERE id = ?", (user['minor_1'],), True) if user['minor_1'] != None else None
        minor_2 = query_db('department', "SELECT * FROM department WHERE id = ?", (user['minor_2'],), True) if user['minor_2'] != None else None
        courseIds_taken = [course['course_id'] for course
                           in query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id = ? AND taken=?",
                           (user['id'], 1))]
        courses_taken = [query_db('course', "SELECT * FROM course WHERE id = ?", (courseId,), True) for courseId in courseIds_taken]
        courseIds_taking = [course['course_id'] for course
                            in query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id = ? AND taking=?",
                            (user['id'], 1))]
        courses_taking = [query_db('course', "SELECT * FROM course WHERE id = ?", (courseId,), True) for courseId in courseIds_taking]

        if user['id'] != session['userid']:
            return render_template("profile.html", user=user, image=image, is_on_campus=is_on_campus,
                                   following=following, followed=followed, followingUsers=followingUsers,
                                   followers=followers, college=college, school=school, major_1=major_1, major_2=major_2,
                                   minor_1=minor_1, minor_2=minor_2, courses_taken=courses_taken, courses_taking=courses_taking,
                                   editable=False)
        else:
            return render_template("profile.html", user=user, image=image, is_on_campus=is_on_campus,
                                   following=following, followed=followed, followingUsers=followingUsers,
                                   followers=followers, college=college, school=school, major_1=major_1, major_2=major_2,
                                   minor_1=minor_1, minor_2=minor_2, courses_taken=courses_taken, courses_taking=courses_taking,
                                   editable=True)

# Profile update page
@app.route("/<int:userid>/edit/", methods=["GET", "POST"])
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
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        if request.method == 'GET':
            user        = query_db('user', "SELECT * FROM user WHERE id = ?", (session["userid"],), True)
            colleges    = query_db('college', "SELECT * FROM college")
            schools     = query_db('school', "SELECT * FROM school WHERE college_id=?", (user['college'],))
            departments = query_db('department', "SELECT * FROM department WHERE college_id=?", (user['college'],))
            return render_template("edit_profile.html", user=user, colleges=colleges, schools=schools, departments=departments)
        elif request.method == 'POST':
            # Avoid storing in session (might confuse users)
            name    = request.form.get("name")
            email   = request.form.get("email")
            college = int(request.form.get("college"))
            school  = int(request.form.get("school")) if request.form.get("school") else None
            gender  = request.form.get("gender") \
                      if (request.form.get("gender") and request.form.get("gender") != 'PNTA') \
                      else 'N/A'
            year    = request.form.get("year") if request.form.get("year") else None
            major_1 = int(request.form.get("major_1")) if request.form.get("major_1") else None
            major_2 = int(request.form.get("major_2")) if request.form.get("major_2") else None
            minor_1 = int(request.form.get("minor_1")) if request.form.get("minor_1") else None
            minor_2 = int(request.form.get("minor_2")) if request.form.get("minor_2") else None
            profile = request.form.get("profile") if request.form.get("profile") else None
            image   = request.files['image'] if ('image' in request.files) else None

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

            # Validate image URL
            if image:
                imageFileName = image.filename
                if ('.' in imageFileName) and (imageFileName.rsplit('.', 1)[1] in ['png', 'jpg', 'jpeg']):
                    image.save('./static/images/' + secure_filename(imageFileName))
                else:
                    flash(u"Invalid file extension. Please upload a file ending with either .png/.jpg/.jpeg.", 'warning')
                    return redirect(url_for("update", userid=session['userid']))
            else:
                imageFileName = query_db('user', "SELECT * FROM User WHERE id = ?", (userid,), True)['image']

            # Update user info in DB only if passed all validations
            modify_db('user', "UPDATE user \
                       SET name=?, email=?, password=?, gender=?, college=?, school=?, year=?, major_1=?, \
                       major_2=?, minor_1=?, minor_2=?, profile=?, image=? WHERE id=?",
                       (name, email, request.form.get("password"), gender, college, school,
                        year, major_1, major_2, minor_1, minor_2, profile, imageFileName, userid))

            flash(u"Your profile has been updated successfully.", 'info')
            return redirect(url_for('profile', userid=session['userid']))

# Password change page
@app.route("/<int:userid>/pwupdate/", methods=["GET", "POST"])
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
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        if request.method == 'GET':
            return render_template("change_password.html")
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

@app.route("/<int:userid>/is_on_campus/", methods=["POST"])
def change_campus_status(userid):
    if int(request.form.get('flag')) == 1:
        modify_db('user', "UPDATE User SET is_on_campus=? WHERE id=?", (1, request.form.get('user_id')))
    else:
        modify_db('user', "UPDATE User SET is_on_campus=? WHERE id=?", (0, request.form.get('user_id')))
    return json.dumps({'res': 'OK'})

@app.route("/<int:userid>/follow/", methods=["POST"])
def follow(userid):
    modify_db('follower', "INSERT INTO Follower (user_id, following_user_id) VALUES(?, ?)",
              (int(userid), request.form.get('following_user_id')))
    followed = True if query_db('follower', "SELECT * FROM Follower WHERE user_id = ? AND following_user_id = ?",
                                (request.form.get('following_user_id'), session['userid']), True) else False
    return json.dumps({'followed': followed})

@app.route("/<int:userid>/unfollow/", methods=["POST"])
def unfollow(userid):
    modify_db('follower', "DELETE FROM Follower WHERE user_id = ? AND following_user_id = ?",
              (int(userid), request.form.get('following_user_id')))
    followed = True if query_db('follower', "SELECT * FROM Follower WHERE user_id = ? AND following_user_id = ?",
                                (request.form.get('following_user_id'), session['userid']), True) else False
    return json.dumps({'followed': followed})

@app.route("/<int:userid>/following/")
def index_following_users(userid):
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        following_user_ids = [following_user['following_user_id'] for following_user \
                              in query_db('follower', "SELECT * FROM Follower WHERE user_id = ?", (userid,))]
        following_users = [query_db('user', "SELECT * FROM User WHERE id = ?", (following_user_id,), True) \
                           for following_user_id in following_user_ids]
        return render_template("index_following_users.html", users=following_users, query_db=query_db)

@app.route("/<int:userid>/followers/")
def index_followers(userid):
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        follower_ids = [follower['user_id'] for follower \
                        in query_db('follower', "SELECT * FROM Follower WHERE following_user_id = ?", (userid,))]
        followers = [query_db('user', "SELECT * FROM User WHERE id = ?", (follower_id,), True) for follower_id in follower_ids]
        return render_template("index_followers.html", users=followers, query_db=query_db)

# User index page
@app.route("/users/")
def index_users():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        users = query_db('user', "SELECT * FROM user")
        return render_template("index_users.html", users=users, query_db=query_db)

# College index page
@app.route("/colleges/")
def index_colleges():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        # Store search info in session for displaying breadcrumb
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        session['courseSearch'] = 'colleges'

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
        # Store search info in session for displaying breadcrumb
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        session['courseSearch'] = 'schools'

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
        # Store search info in session for displaying breadcrumb
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        session['courseSearch'] = 'departments'

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
        # Store search info in session for displaying breadcrumb
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        session['courseSearch'] = 'courses'

        courses = query_db('course', "SELECT * FROM course WHERE college_id=? AND school_id=? AND department_id=?",
                           (request.args.get('collegeid', 1), request.args.get('schoolid', 1),
                            request.args.get('departmentid', 1)))
        coursesWithStats = []
        for course in courses:
            if (query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=? AND taken=?", (session['userid'], course['id'], True))
               or query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=? AND taking=?", (session['userid'], course['id'], True))):
                coursesWithStats.append({'course': course, 'taken': True})
            else:
                coursesWithStats.append({'course': course, 'taken': False})

        return render_template("index_courses.html", coursesWithStats=coursesWithStats, request=request)

# Course description page
@app.route("/course/")
def viewCourse():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        # Store search info in session for displaying breadcrumb
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        session['courseSearch'] = 'course'

        course = query_db('course', "SELECT * FROM course WHERE college_id=? AND school_id=? AND department_id=? AND id=?",
                          (request.args.get('collegeid', 1), request.args.get('schoolid', 1),
                           request.args.get('departmentid', 1), request.args.get('courseid', 1)), True)
        taking = True if query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=? AND taking=?",
                                  (session['userid'], course['id'], 1), True) else False
        if taking:
            taken = False
        else:
            if not query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=?",
                            (session['userid'], course['id']), True):
                taken = False
            else:
                taken = True if query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=?",
                                         (session['userid'], course['id']), True)['taken'] == 1 else False

        reviews = query_db('course_review', "SELECT * FROM CourseReview WHERE course_id=?", (course['id'],))
        wroteReview = True if query_db('course_review', "SELECT * FROM CourseReview WHERE user_id=? AND course_id=?",
                                       (session['userid'], course['id']), True) else False

        # Have to convert Row object to list or dict to properly parse data in JS
        reviews_for_graphs = []
        for review in reviews:
            reviews_for_graphs.append({key: review[key] for key in review.keys()})

        return render_template("course_profile.html",
                               course=course,
                               taken=taken,
                               taking=taking,
                               reviews=reviews,
                               reviews_for_graphs=reviews_for_graphs,
                               wroteReview=wroteReview)

# Handles Ajax requests and returns json
@app.route("/course/save/", methods=["POST"])
def saveAsTaken():
    if int(request.form.get('cancel')) == 0:
        # Make sure to deal with users who heavily use browser's back/forward buttons
        if not query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=?",
                        (session['userid'], int(request.form.get('courseId')))):
            if int(request.form.get('taking')) == 0:
                modify_db('course_taken', "INSERT INTO CourseTaken (user_id, course_id, taken, taking) VALUES(?, ?, ?, ?)",
                          (session['userid'], int(request.form.get('courseId')), 1, 0))
            else:
                modify_db('course_taken', "INSERT INTO CourseTaken (user_id, course_id, taken, taking) VALUES(?, ?, ?, ?)",
                          (session['userid'], int(request.form.get('courseId')), 0, 1))
        else:
            if int(request.form.get('taking')) == 0:
                modify_db('course_taken', "UPDATE CourseTaken SET taken=?, taking=? WHERE user_id=? AND course_id=?",
                          (1, 0, session['userid'], int(request.form.get('courseId'))))
            else:
                modify_db('course_taken', "UPDATE CourseTaken SET taken=?, taking=? WHERE user_id=? AND course_id=?",
                          (0, 1, session['userid'], int(request.form.get('courseId'))))
    else:
        # Make sure to deal with users who heavily use browser's back/forward buttons
        if query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=?",
                    (session['userid'], int(request.form.get('courseId')))):
            if int(request.form.get('taking')) == 0:
                modify_db('course_taken', "UPDATE CourseTaken SET taken=? WHERE user_id=? AND course_id=?",
                          (0, session['userid'], int(request.form.get('courseId'))))
            else:
                modify_db('course_taken', "UPDATE CourseTaken SET taking=? WHERE user_id=? AND course_id=?",
                          (0, session['userid'], int(request.form.get('courseId'))))

            courseUpdated = query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=?",
                                     (session['userid'], int(request.form.get('courseId'))), True)

            # If both are set to 0, delete data from DB
            if courseUpdated['taken'] == 0 and courseUpdated['taking'] == 0:
                modify_db('course_taken', "DELETE FROM CourseTaken WHERE user_id=? AND course_id=?",
                          (session['userid'], int(request.form.get('courseId'))))

    return json.dumps({'cancel': request.form.get('cancel'), 'taking': request.form.get('taking')})

# Course review page
@app.route("/write_review/", methods=["GET", "POST"])
def writeCourseReview():
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    else:
        if 'courseSearch' in session:
            session.pop('courseSearch', None)
        if request.method == 'GET':
            course = query_db('course', "SELECT * FROM course WHERE id=?", (request.args.get('courseid'),), True)
            if request.args.get('wroteReview'):
                review = query_db('course_review', "SELECT * FROM CourseReview WHERE user_id=? AND course_id=?",
                                  (session['userid'], request.args.get('courseid')), True)
                return render_template("edit_course_review.html", course=course, review=review)
            else:
                return render_template("edit_course_review.html", course=course, review=None)
        elif request.method == 'POST':
            course = query_db('course_taken', "SELECT * FROM CourseTaken WHERE user_id=? AND course_id=?",
                              (session['userid'], int(request.args.get('courseid'))), True)
            # If user tries to write a review for any course not yet taken by directly modifying query strings
            if not course or course['taken'] == False:
                courseinfo = query_db('course', "SELECT * FROM Course WHERE id=?", (request.args.get('courseid'),), True)
                flash(u"You cannot write a review for any course not yet taken.", 'warning')
                return redirect(url_for('viewCourse', collegeid=courseinfo['college_id'],
                                                      schoolid=courseinfo['school_id'],
                                                      departmentid=courseinfo['department_id'],
                                                      courseid=courseinfo['id']))
            else:
                rating     = int(request.form.get("rating"))
                difficulty = int(request.form.get("difficulty"))
                term       = request.form.get("term").upper()
                professor  = request.form.get("professor").upper()
                comment    = request.form.get("comment") if request.form.get("comment") else None
                review = query_db('course_review', "SELECT * FROM CourseReview WHERE user_id=? AND course_id=?",
                                  (session['userid'], request.args.get('courseid')), True)
                # If updating stale review
                if review:
                    modify_db('course_review', "UPDATE CourseReview \
                               SET rating=?, difficulty=?, term=?, professor=?, comment=? \
                               WHERE user_id=? AND course_id=?",
                               (rating, difficulty, term, professor, comment, session['userid'], request.args.get('courseid')))

                    flash(u"Your review has been updated successfully.", 'info')

                # If submitting new review
                else:
                    modify_db('course_review', "INSERT INTO CourseReview \
                               (user_id, course_id, rating, difficulty, term, professor, comment) \
                               VALUES(?, ?, ?, ?, ?, ?, ?)",
                               (session['userid'], request.args.get('courseid'), rating, difficulty, term, professor, comment))

                    flash(u"Your review has been submitted successfully.", 'info')

                courseinfo = query_db('course', "SELECT * FROM Course WHERE id=?", (request.args.get('courseid'),), True)
                return redirect(url_for('viewCourse', collegeid=courseinfo['college_id'],
                                                      schoolid=courseinfo['school_id'],
                                                      departmentid=courseinfo['department_id'],
                                                      courseid=courseinfo['id']))

### Messaging Feature ###

@app.route("/<int:userid>/messages/")
def showMessagesAll(userid):
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    # If not valid user (when trying to see others' messages)
    if int(userid) != session['userid']:
        flash(u"Invalid access. You cannot see other users' message log.", 'warning')
        return redirect(url_for("showMessagesAll", userid=session['userid']))
    else:
        if 'courseSearch' in session:
            session.pop('courseSearch', None)

        # Should be modified later; add friend feature and show only those who have been added as friends
        friends = query_db('user', "SELECT * FROM User")
        rooms   = query_db('room', "SELECT * FROM Room WHERE user_id=?", (userid,))
        if len(rooms) == 0:
            roomsStats = []
            return render_template("messages.html", friends=friends, roomsStats=roomsStats, messagesWithUserInfo=None, selectedRoomID=None)
        else:
            roomsStats = []
            for room in rooms:
                # If it's an empty room (no messages, only available for group chatting)
                if query_db('message', "SELECT * FROM Message WHERE room_id=?", (room['id'],), True) == None:
                    seenAll = True
                # If someone else sent message(s), but the user hasn't seen anything in that room yet
                elif query_db('message_seen', "SELECT * FROM MessageSeen WHERE user_id=? AND room_id=?", (userid, room['id']), True) == None:
                    seenAll = False
                else:
                    lastMessage = query_db('message',
                                           "SELECT * FROM Message WHERE room_id=? ORDER BY id DESC LIMIT 1",
                                           (room['id'],), True)
                    # Check if the user has already seen all the messages in that room
                    if lastMessage['id'] == query_db('message_seen', "SELECT * FROM MessageSeen WHERE user_id=? AND room_id=?", (userid, room['id']), True)['last_seen_msg_id']:
                        seenAll = True
                    else:
                        seenAll = False

                roomsWithThatID = query_db('room', "SELECT * FROM Room WHERE id=?", (room['id'],))
                users = []
                # If there's only one user within that room
                if len(roomsWithThatID) == 1:
                    roomsStats.append({
                        'id': roomsWithThatID[0]['id'],
                        'users': users,
                        'seenAll': seenAll,
                        'inactive': True
                    })
                else:
                    for roomWithThatID in roomsWithThatID:
                        if roomWithThatID['user_id'] != userid:
                            users.append(query_db('user', "SELECT * FROM User WHERE id=?", (roomWithThatID['user_id'],), True))
                    roomsStats.append({
                        'id': roomWithThatID['id'],
                        'users': users,
                        'seenAll': seenAll,
                        'inactive': False
                    })

            return render_template("messages.html", friends=friends, roomsStats=roomsStats, messagesWithUserInfo=None, selectedRoomID=None)

@app.route("/<int:userid>/messages/<int:roomid>/")
def showMessages(userid, roomid):
    # If not logged in
    if 'userid' not in session:
        flash(u"You're not logged in. Please log in first to see the content.", 'warning')
        return redirect(url_for("login"))
    # If not valid user (when trying to see others' messages)
    if int(userid) != session['userid']:
        flash(u"Invalid access. You cannot see other users' message log.", 'warning')
        return redirect(url_for("showMessagesAll", userid=session['userid']))
    # If user tries to access a room that the user isn't joined
    if (roomid != 0) and (roomid not in [room['id'] for room in query_db('room', "SELECT * FROM Room WHERE user_id=?", (userid,))]):
        flash(u"Invalid access.", 'warning')
        return redirect(url_for("showMessagesAll", userid=session['userid']))
    else:
        if 'courseSearch' in session:
            session.pop('courseSearch', None)

        # Should be modified later; add friend feature and show only those who have been added as friends
        friends = query_db('user', "SELECT * FROM User")

        rooms = query_db('room', "SELECT * FROM Room WHERE user_id=?", (userid,))
        if len(rooms) == 0:
            roomsStats = []
            return render_template("messages.html",
                                   friends=friends, roomsStats=roomsStats, selectedRoomID=roomid,
                                   chatScreen=True, messagesWithUserInfo=None, datetime=datetime)
        else:
            roomsStats = []
            # Check whether room is selected from search box (if so roomid == 0)
            if roomid != 0:
                # Set up roomsStats
                for room in rooms:
                    # If it's an empty room (no messages, only available for group chatting)
                    if query_db('message', "SELECT * FROM Message WHERE room_id=?", (room['id'],)) == None:
                        seenAll = True
                    else:
                        lastMessage = query_db('message',
                                               "SELECT * FROM Message WHERE room_id=? ORDER BY id DESC LIMIT 1",
                                               (room['id'], ), True)
                        if room['id'] == roomid:
                            # If someone else sent message(s), but the user hasn't seen anything in that room yet
                            if query_db('message_seen', "SELECT * FROM MessageSeen WHERE user_id=? AND room_id=?", (userid, room['id']), True) == None:
                                if lastMessage != None:
                                    modify_db('message_seen',
                                              "INSERT INTO MessageSeen (user_id, last_seen_msg_id, room_id) VALUES(?, ?, ?)",
                                              (userid, room['id'], lastMessage['id']))
                            else:
                                # Record that user has seen the latest message sent to this room
                                modify_db('message_seen',
                                          "UPDATE MessageSeen SET last_seen_msg_id=? WHERE user_id=? AND room_id=?",
                                          (lastMessage['id'], userid, room['id']))
                            seenAll = True
                        else:
                            if query_db('message_seen', "SELECT * FROM MessageSeen WHERE user_id=? AND room_id=?", (userid, room['id']), True) != None:
                                # Check if the user has already seen all the messages in that room
                                if lastMessage['id'] == query_db('message_seen', "SELECT * FROM MessageSeen WHERE user_id=? AND room_id=?", (userid, room['id']), True)['last_seen_msg_id']:
                                    seenAll = True
                                else:
                                    seenAll = False

                    roomsWithThatID = query_db('room', "SELECT * FROM Room WHERE id=?", (room['id'],))
                    users = []
                    # If there's only one user within that room
                    if len(roomsWithThatID) == 1:
                        roomsStats.append({
                            'id': roomsWithThatID[0]['id'],
                            'users': users,
                            'seenAll': seenAll,
                            'inactive': True
                        })
                    else:
                        for roomWithThatID in roomsWithThatID:
                            if roomWithThatID['user_id'] != userid:
                                users.append(query_db('user', "SELECT * FROM User WHERE id=?", (roomWithThatID['user_id'],), True))
                        roomsStats.append({
                            'id': roomWithThatID['id'],
                            'users': users,
                            'seenAll': seenAll,
                            'inactive': False
                        })

                # Set up messagesWithUserInfo
                messages = query_db('message', "SELECT * FROM Message WHERE room_id=?", (roomid,))

                messagesWithUserInfo = []
                for message in messages:
                    user = query_db('user', "SELECT * FROM User WHERE id=?", (message['sender_id'],), True)
                    messagesWithUserInfo.append({
                        'message_object': dict(message),
                        'user_id': user['id'],
                        'user_name': user['name'],
                        'user_image': '/static/images/'+user['image']
                    })

                return render_template("messages.html",
                                       friends=friends, roomsStats=roomsStats, selectedRoomID=roomid,
                                       chatScreen=True, messagesWithUserInfo=messagesWithUserInfo, datetime=datetime)
            # If roomid == 0
            else:
                # Set up roomsStats
                for room in rooms:
                    # If it's an empty room (no messages, only available for group chatting)
                    if query_db('message', "SELECT * FROM Message WHERE room_id=?", (room['id'],)) == None:
                        seenAll = True
                    else:
                        lastMessage = query_db('message',
                                               "SELECT * FROM Message WHERE room_id=? ORDER BY id DESC LIMIT 1",
                                               (room['id'],), True)
                        if query_db('message_seen', "SELECT * FROM MessageSeen WHERE user_id=? AND room_id=?", (userid, room['id']), True) != None:
                            # Check if the user has already seen all the messages in that room
                            if lastMessage['id'] == query_db('message_seen', "SELECT * FROM MessageSeen WHERE user_id=? AND room_id=?", (userid, room['id']), True)['last_seen_msg_id']:
                                seenAll = True
                            else:
                                seenAll = False
                        else:
                            seenAll = None

                    roomsWithThatID = query_db('room', "SELECT * FROM Room WHERE id=?", (room['id'],))
                    users = []
                    # If there's only one user within that room
                    if len(roomsWithThatID) == 1:
                        roomsStats.append({
                            'id': roomsWithThatID[0]['id'],
                            'users': users,
                            'seenAll': seenAll,
                            'inactive': True
                        })
                    else:
                        for roomWithThatID in roomsWithThatID:
                            if roomWithThatID['user_id'] != userid:
                                users.append(query_db('user', "SELECT * FROM User WHERE id=?", (roomWithThatID['user_id'],), True))
                        roomsStats.append({
                            'id': roomWithThatID['id'],
                            'users': users,
                            'seenAll': seenAll,
                            'inactive': False
                        })

                # Set up messagesWithUserInfo
                if not request.args.get('receiverid'):
                    return redirect(url_for("showMessagesAll", userid=session['userid']))

                receiverid = int(request.args.get('receiverid'))
                # If receiverid doesn't exist (i.e. user doesn't exist)
                if not (query_db('user', "SELECT * FROM User WHERE id=?", (receiverid,), True)):
                    flash(u"Specified user doesn't exist.", 'warning')
                    return redirect(url_for("showMessagesAll", userid=session['userid']))
                # If userid == receiverid (just for convenience)
                if int(userid) == receiverid:
                    flash(u"You cannot chat with yourself.", 'warning')
                    return redirect(url_for("showMessagesAll", userid=session['userid']))
                else:
                    if (query_db('room', "SELECT * FROM Room WHERE user_id = ?", (userid,)) == None) \
                        or (query_db('room', "SELECT * FROM Room WHERE user_id = ?", (receiverid,)) == None):
                        messagesWithUserInfo = None
                    else:
                        room_ids_sender   = set([room['id'] for room in query_db('room', "SELECT * FROM Room WHERE user_id = ?", (userid,))])
                        room_ids_receiver = set([room['id'] for room in query_db('room', "SELECT * FROM Room WHERE user_id = ?", (receiverid,))])
                        room_ids_common   = list(room_ids_sender.intersection(room_ids_receiver))
                        if room_ids_common == None:
                            messagesWithUserInfo = None
                        else:
                            flags = [False for i in range(len(room_ids_common))]     # Need a new room?
                            for i in range(len(room_ids_common)):
                                rooms = query_db('room', "SELECT * FROM Room WHERE id = ?", (room_ids_common[i],))
                                for room in rooms:
                                    if (room['user_id'] != userid and room['user_id'] != receiverid):
                                        flags[i] = True
                                        break
                                if flags[i] == False:
                                    room_id = room_ids_common[i]
                                    break
                            # Check if there already exists a room only between the two
                            if all(flags):
                                messagesWithUserInfo = None
                            else:
                                messages = query_db('message', "SELECT * FROM Message WHERE room_id = ?", (room_id,))
                                messagesWithUserInfo = []
                                for message in messages:
                                    user = query_db('user', "SELECT * FROM User WHERE id=?", (message['sender_id'],), True)
                                    messagesWithUserInfo.append({
                                        'message_object': dict(message),
                                        'user_id': user['id'],
                                        'user_name': user['name'],
                                        'user_image': '/static/images/'+user['image']
                                    })

                    if messagesWithUserInfo:
                        return render_template("messages.html",
                                               friends=friends, roomsStats=roomsStats, selectedRoomID=room_id,
                                               chatScreen=True, messagesWithUserInfo=messagesWithUserInfo, datetime=datetime)
                    else:
                        user = query_db('user', "SELECT * FROM User WHERE id=?", (receiverid,), True)
                        roomsStats.append({'id': 0, 'users': [user]})
                        return render_template("messages.html",
                                               friends=friends, roomsStats=roomsStats, selectedRoomID=0,
                                               chatScreen=True, messagesWithUserInfo=messagesWithUserInfo, datetime=datetime)

# Remove user from the specified room
@app.route("/<int:userid>/leave_room/", methods=["POST"])
def leaveRoom(userid):
    # Delete messages if all the users within that room left
    if len(query_db('room', "SELECT * FROM Room WHERE id=?", (int(request.form.get('room_id')),))) == 1:
        modify_db('message', "DELETE FROM Message WHERE room_id=?", (int(request.form.get('room_id')),))
    flash(u"You've successfully left a chat room.", 'info')
    modify_db('room', "DELETE FROM Room WHERE id=? AND user_id=?", (int(request.form.get('room_id')), userid))
    return json.dumps({'redirectURL': "/"+str(userid)+"/messages/"})

@socketio.on('connect')
def connect():
    print('Connected! Joining rooms the user belongs.')
    rooms = query_db('room', "SELECT * FROM Room WHERE user_id = ?", (session['userid'],))
    if rooms != None:
        for room in rooms:
            join_room(room['id'])

@socketio.on('disconnect')
def disconnect():
    print('Disconnected. Leaving all the rooms...')
    rooms = query_db('room', "SELECT * FROM Room WHERE user_id = ?", (session['userid'],))
    if rooms != None:
        for room in rooms:
            leave_room(room['id'])

# Store sent message in DB
@socketio.on('reflectMsg')
def on_msg_sent(data):
    sender_id = int(data['sender_id'])
    message   = data['message']
    timestamp = str(data['timestamp'])

    # Set up a room to send a message
    if 'receiver_id' in data:     # Need a new room?
        receiver_id = int(data['receiver_id'])
        rooms = query_db('room', "SELECT * FROM Room")
        room_id = (1 + max([room['id'] for room in rooms])) if rooms else 1
        modify_db('room', "INSERT INTO Room (id, user_id, created_at) VALUES(?, ?, ?)", (room_id, sender_id, timestamp))
        modify_db('room', "INSERT INTO Room (id, user_id, created_at) VALUES(?, ?, ?)", (room_id, receiver_id, timestamp))
    else:
        room_id = int(data['room_id'])

    modify_db('message', "INSERT INTO Message (room_id, sender_id, message, sent_at) VALUES(?, ?, ?, ?)",
              (room_id, sender_id, message, timestamp))

    # Set seen status for sender (sender has already seen all the messages, including the message just sent)
    if query_db('message_seen', "SELECT * FROM MessageSeen WHERE user_id=? AND room_id=?", (sender_id, room_id), True) == None:
        modify_db('message_seen', "INSERT INTO MessageSeen (user_id, room_id, last_seen_msg_id) VALUES(?, ?, ?)",
                  (sender_id, room_id, query_db('message', "SELECT * FROM Message WHERE room_id=? ORDER BY id DESC LIMIT 1", (room_id, ), True)['id']))
    else:
        modify_db('message_seen', "UPDATE MessageSeen SET last_seen_msg_id=?",
                  (query_db('message', "SELECT * FROM Message WHERE room_id=? ORDER BY id DESC LIMIT 1", (room_id, ), True)['id'],))

    join_room(room_id)

    user = query_db('user', "SELECT * FROM User WHERE id=?", (sender_id,), True)
    messagesWithUserInfo = {
        'message_object': dict(query_db('message', "SELECT * FROM Message WHERE room_id = ? AND sender_id = ? AND sent_at =?",
                                        (room_id, sender_id, timestamp), True)),
        'user_id': user['id'],
        'user_name': user['name'],
        'user_image': '/static/images/'+user['image']
    }

    emit('showMsg', messagesWithUserInfo, room=room_id)

# Set up a room for group chatting
@socketio.on('setUpGroupChat')
def setUpGroupChat(data):
    members = [int(e) for e in json.loads((data['groupMembers']))]
    timestamp = data['timestamp']
    # If only one user is selected
    if len(members) == 1:
        # B.c. Flask's redirect doen't work in socketio
        emit('redirect', {'url': url_for('showMessages', userid=session['userid'], roomid=0, receiverid=members[0])})
    else:
        # Check if a room with those users already exists
        room_exists = False
        for i in range(len(members)):
            if i == 0:
                room_ids_1 = set([room['id'] for room in query_db('room', "SELECT * FROM Room WHERE user_id = ?", (members[i],))])
                room_ids_2 = {}
                room_ids_common = []
            elif i == 1:
                room_ids_2 = room_ids_1
                room_ids_1 = set([room['id'] for room in query_db('room', "SELECT * FROM Room WHERE user_id = ?", (members[i],))])
                room_ids_common = list(room_ids_1.intersection(room_ids_2))
                if len(room_ids_common) == 0:
                    break
            else:
                room_ids = set([room['id'] for room in query_db('room', "SELECT * FROM Room WHERE user_id = ?", (members[i],))])
                room_ids_common = list(set(room_ids_common).intersection(room_ids))
                if len(room_ids_common) == 0:
                    break
        else:    # this block runs only when for-loop above terminates without break
            for room_id_common in room_ids_common:
                if set([room['user_id'] for room in query_db('room', "SELECT * FROM Room WHERE id=?", (room_id_common,))]) == set(members+[int(session['userid'])]):
                    room_exists = True
                    room_id = room_id_common
                    break

        if room_exists:
            emit('redirect', {'url': url_for('showMessages', userid=session['userid'], roomid=room_id)})
        else:     # If new room is created
            rooms = query_db('room', "SELECT * FROM Room")
            room_id = (1 + max([room['id'] for room in rooms])) if rooms else 1
            modify_db('room', "INSERT INTO Room (id, user_id, created_at) VALUES(?, ?, ?)", (room_id, int(session['userid']), timestamp))
            for member in members:
                modify_db('room', "INSERT INTO Room (id, user_id, created_at) VALUES(?, ?, ?)", (room_id, member, timestamp))

            roomsWithThatID = query_db('room', "SELECT * FROM Room WHERE id=?", (room_id,))
            users = []
            # If there's only one user within that room
            if len(roomsWithThatID) == 1:
                newRoom = {
                    'id': roomsWithThatID[0]['id'],
                    'users': users,
                    'inactive': 1
                }
            else:
                for roomWithThatID in roomsWithThatID:
                    if roomWithThatID['user_id'] != int(session['userid']):
                        users.append(dict(query_db('user', "SELECT * FROM User WHERE id=?", (roomWithThatID['user_id'],), True)))
                newRoom = {
                    'id': roomWithThatID['id'],
                    'users': users,
                    'inactive': 0
                }

            emit('reflectNewRoom', newRoom)

# For notification purpose (not available yet)
# @socketio.on('broadcast')
# def on_broadcast(data):
#     msg = data['msg']
#     time = str(data['timestamp'])
#     emit('showMsg', msg+' at '+time, broadcast=True)

### Messaging Feature End ###

# Necessary to make Ajax work correctly
@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
  return response

# Driver
if __name__ == '__main__':
    app.secret_key = SECRET_KEY
    socketio.run(app, debug="True")
