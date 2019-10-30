CREATE TABLE Department (
  id         INTEGER,
  college_id INTEGER,
  school_id  INTEGER,
  department VARCHAR(255) UNIQUE,
  link       TEXT UNIQUE,
  PRIMARY KEY(id, college_id, school_id)
);
