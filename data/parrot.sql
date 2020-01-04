DROP TABLE IF EXISTS Responses;
DROP TABLE IF EXISTS Triggers;
DROP TABLE IF EXISTS Parrots;

CREATE TABLE Parrots
(
    ParrotID serial
);

CREATE TABLE Triggers
(
    ParrotID int,
    Trigger  varchar(255),
    Alias    bool
);

CREATE TABLE Responses
(
    ParrotID int,
    Response varchar(255)
);

-- create
WITH id AS (INSERT INTO Parrots DEFAULT VALUES RETURNING ParrotID),
     trigger_insert AS (
         INSERT INTO Triggers (ParrotID, Trigger, Alias)
             VALUES (id, %s, true) RETURNING ParrotID
     )
INSERT INTO Responses (ParrotID, Response) VALUES (id, %s);

-- get parrotid from name
SELECT ParrotID FROM Triggers WHERE Trigger LIKE %s ESCAPE '';

-- delete
DELETE FROM Triggers
    WHERE Trigger LIKE '%s'
    ESCAPE ''
    RETURNING ParrotID, Alias;

-- delete all
DELETE FROM Triggers WHERE ParrotID=%s;
DELETE FROM Responses WHERE ParrotID=%s;

-- get random response

