CREATE TABLE School (
  id         INTEGER PRIMARY KEY,
  college_id INTEGER,
  name       VARCHAR(255),
  link       TEXT UNIQUE
);
