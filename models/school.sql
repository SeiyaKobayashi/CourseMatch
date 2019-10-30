CREATE TABLE School (
  id         INTEGER,
  college_id INTEGER,
  school     VARCHAR(255) UNIQUE,
  PRIMARY KEY(id, college_id)
);
