CREATE TABLE User (
  id       INTEGER PRIMARY KEY,
  name     VARCHAR(255),
  email    VARCHAR(255) UNIQUE,
  password VARCHAR(255),
  gender   VARCHAR(255),
  school   VARCHAR(255),
  year     VARCHAR(255),
  major    VARCHAR(255),
  minor    VARCHAR(255),
  courses  VARCHAR(255)
);
