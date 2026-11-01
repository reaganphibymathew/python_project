-- Run this ONCE before running the Python program.

CREATE DATABASE IF NOT EXISTS court_booking;
USE court_booking;

-- Table 1: the courts
CREATE TABLE IF NOT EXISTS courts (
    court_id   INT AUTO_INCREMENT PRIMARY KEY,
    court_name VARCHAR(50) NOT NULL
);

-- Table 2: the time slots
CREATE TABLE IF NOT EXISTS time_slots (
    slot_id   INT AUTO_INCREMENT PRIMARY KEY,
    slot_time VARCHAR(5) NOT NULL
);

-- Table 3: the bookings (links to courts and time_slots)
CREATE TABLE IF NOT EXISTS bookings (
    booking_id   INT AUTO_INCREMENT PRIMARY KEY,
    student_id   VARCHAR(20) NOT NULL,
    student_name VARCHAR(50) NOT NULL,
    court_id     INT NOT NULL,
    slot_id      INT NOT NULL,
    booking_date DATE NOT NULL,
    FOREIGN KEY (court_id) REFERENCES courts(court_id),
    FOREIGN KEY (slot_id) REFERENCES time_slots(slot_id),
    -- the database itself refuses a double booking
    UNIQUE (court_id, slot_id, booking_date)
);

-- Starting data
INSERT INTO courts (court_name) VALUES
    ('Badminton'), ('Tennis'), ('Basketball'), ('Squash');

INSERT INTO time_slots (slot_time) VALUES
    ('09:00'), ('10:00'), ('11:00'), ('12:00'),
    ('14:00'), ('15:00'), ('16:00'), ('17:00');
