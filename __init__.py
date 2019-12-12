from init_db import app, init_db, get_db, modify_db, query_db
from scraping import scrapeSchools, scrapeDepartments, scrapeCourses
from os import path

# Function to be run before app starts running for the first time
def init_app():
    if not path.exists("models/user.db"):
        print('Initializing "user.db"...')
        init_db("user")
        print('Done.')

    if not path.exists("models/room.db"):
        print('Initializing "room.db"...')
        init_db("room")
        print('Done.')

    if not path.exists("models/message.db"):
        print('Initializing "message.db"...')
        init_db("message")
        print('Done.')

    if not path.exists("models/course_taken.db"):
        print('Initializing "course_taken.db"...')
        init_db("course_taken")
        print('Done.')

    if not path.exists("models/course_review.db"):
        print('Initializing "course_review.db"...')
        init_db("course_review")
        print('Done.')

    if not path.exists("models/college.db"):
        print('Initializing "college.db"...')
        init_db("college")
        # should be modified later
        modify_db('college', "INSERT INTO college (name, link) VALUES(?, ?)",
                  ('Boston University', 'https://www.bu.edu/academics/schools-colleges/'))
        print('Done.')

    if not path.exists("models/school.db"):
        print('Initializing "school.db"...')
        init_db("school")
        colleges = query_db('college', "SELECT * FROM college")
        for college in colleges:
            schools = scrapeSchools(college['link'])
            for i in range(len(schools)):
                modify_db('school', "INSERT INTO school (college_id, name, link) VALUES(?, ?, ?)",
                          (college['id'], schools[i]['school'], schools[i]['link']))
        print('Done.')

    if not path.exists("models/department.db"):
        print('Initializing "department.db"...')
        init_db("department")
        colleges = query_db('college', "SELECT * FROM college")
        for college in colleges:
            schools = query_db('school', "SELECT * FROM school WHERE college_id=?", (college['id'],))
            for school in schools:
                departments = scrapeDepartments(school['link'])
                for i in range(len(departments)):
                    modify_db('department', "INSERT INTO department (college_id, school_id, name, link) VALUES(?, ?, ?, ?)",
                              (college['id'], school['id'], departments[i]['department'], departments[i]['link']))
        print('Done.')

    if not path.exists("models/course.db"):
        print('Initializing "course.db"...')
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
                        modify_db('course', "INSERT INTO course (college_id, school_id, department_id, name, link) \
                                  VALUES(?, ?, ?, ?, ?)",
                                  (college['id'], school['id'], department['id'],
                                  courses[i]['course'], courses[i]['link']))
        print('Done.')

if __name__ == '__main__':
    with app.app_context():
        print('Executing "init_app()"...')
        init_app()
        print('All done.')
