CREATE TABLE MessageSeen (
  id               INTEGER PRIMARY KEY,
  user_id          INTEGER,
  room_id          INTEGER,
  last_seen_msg_id INTEGER
);
