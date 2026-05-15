-- DROP TABLE [FOOTYHUB].[dbo].[articles]
CREATE TABLE [dbo].[articles] (
    [id]               INT            IDENTITY(1,1)  NOT NULL,
    [source_type]      VARCHAR(100)                  NOT NULL,
    [source_name]      VARCHAR(200)                  NOT NULL,
    [source_record_id] VARCHAR(500)                  NOT NULL,
    [source_url]       VARCHAR(1000)                 NULL,
    [title]            NVARCHAR(500)                 NULL,
    [body_text]        NVARCHAR(MAX)                 NULL,
    [published_at]     VARCHAR(20)                   NULL,
    [topic]            VARCHAR(100)                  NULL,
    [competition]      VARCHAR(100)                  NULL,
    [club]             NVARCHAR(200)                 NULL,
    [player_name]      NVARCHAR(200)                 NULL,
    [theme]            VARCHAR(100)                  NULL,
    [clubs_mentioned]  NVARCHAR(500)                 NULL,
    [players_mentioned] NVARCHAR(500)                NULL,
    [created_at]       DATETIME2                     NOT NULL DEFAULT GETDATE(),
    CONSTRAINT PK_articles PRIMARY KEY ([id]),
    CONSTRAINT UQ_articles UNIQUE ([source_type], [source_name], [source_record_id])
);