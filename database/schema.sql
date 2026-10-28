CREATE DATABASE Personalised_Medicine_Recommendation_System;

USE Personalised_Medicine_Recommendation_System;

CREATE TABLE medicines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    usage_note TEXT
);

CREATE TABLE symptom_checks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    symptoms TEXT NOT NULL,
    duration VARCHAR(100),
    demo_prediction VARCHAR(120) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role ENUM('user', 'assistant') NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE diet_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL
);

INSERT INTO medicines
(name, category, description, usage_note)
VALUES
(
    'Oral rehydration salts (ORS)',
    'Hydration',
    'A product used to replace fluids and electrolytes.',
    'Follow package directions and ask a pharmacist if unsure.'
),
(
    'Paracetamol',
    'Pain relief',
    'A common medicine used for pain or fever.',
    'Use only as directed on the label or by a qualified clinician.'
);

INSERT INTO diet_recommendations
(title, description, category)
VALUES
(
    'Balanced meals',
    'Choose a variety of vegetables, fruit, whole grains, and protein.',
    'General wellness'
),
(
    'Hydration',
    'Drink fluids regularly; individual needs vary.',
    'General wellness'
);

SHOW TABLES;
