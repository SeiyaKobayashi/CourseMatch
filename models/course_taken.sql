CREATE TABLE CourseTaken (
  id         INTEGER PRIMARY KEY,
  user_id    INTEGER,
  course_id  INTEGER,
  taken      BOOLEAN,
  taking     BOOLEAN
);
