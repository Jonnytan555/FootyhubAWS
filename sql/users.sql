CREATE TABLE dbo.users (
    id            INT IDENTITY PRIMARY KEY,
    username      NVARCHAR(100) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    created_at    DATETIME DEFAULT GETDATE()
);