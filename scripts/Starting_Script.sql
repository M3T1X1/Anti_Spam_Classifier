CREATE TABLE "messages" (
  "message_id" integer PRIMARY KEY,
  "sender" varchar,
  "receiver" varchar,
  "value" varchar(10000),
  "is_ham" boolean,
  "created_at" timestamp
);

CREATE TABLE "users" (
  "email" varchar PRIMARY KEY,
  "password" varchar,
  "name" varchar,
  "surname" varchar,
  "role" varchar,
  "position_id" integer,
  "created_at" timestamp,
  "modified_at" timestamp
);

CREATE TABLE "plots" (
  "plot_id" integer PRIMARY KEY,
  "user_id" integer,
  "path" varchar,
  "plot_name" varchar
);

CREATE TABLE "positions" (
  "position_id" integer PRIMARY KEY,
  "title" varchar,
  "expirience_level" varchar
);

ALTER TABLE "messages" ADD FOREIGN KEY ("sender") REFERENCES "users" ("email") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "messages" ADD FOREIGN KEY ("receiver") REFERENCES "users" ("email") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "users" ADD FOREIGN KEY ("position_id") REFERENCES "positions" ("position_id") DEFERRABLE INITIALLY IMMEDIATE;
