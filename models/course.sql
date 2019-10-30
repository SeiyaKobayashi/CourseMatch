CREATE TABLE Course (
  id            INTEGER,
  college_id    INTEGER,
  school_id     INTEGER,
  department_id INTEGER,
  course        VARCHAR(255),
  link          TEXT,
  description   TEXT,
  PRIMARY KEY(id, college_id, school_id, department_id)
);
