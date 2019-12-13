CREATE TABLE User (
  id           INTEGER PRIMARY KEY,
  name         VARCHAR(255),
  email        VARCHAR(255) UNIQUE,
  password     VARCHAR(255),
  gender       VARCHAR(255),
  college      INTEGER,
  school       INTEGER,
  year         VARCHAR(255),
  major_1      INTEGER,
  major_2      INTEGER,
  minor_1      INTEGER,
  minor_2      INTEGER,
  profile      TEXT,
  is_on_campus BOOLEAN,
  image        TEXT
);
