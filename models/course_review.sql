CREATE TABLE CourseReview (
  id         INTEGER PRIMARY KEY,
  user_id    INTEGER,
  course_id  INTEGER,
  rating     INTEGER,
  difficulty INTEGER,
  term       VARCHAR(255),
  professor  VARCHAR(255),
  comment    TEXT
);
