CREATE TABLE Message (
  id        INTEGER PRIMARY KEY,
  room_id   INTEGER,
  sender_id INTEGER,
  message   TEXT,
  sent_at   TEXT
);
