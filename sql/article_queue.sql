-- DROP TABLE [FOOTYHUB].[dbo].[article_queue]
CREATE TABLE [dbo].[article_queue] (
    [id]               INT            IDENTITY(1,1)  NOT NULL,
    [source_type]      VARCHAR(100)                  NOT NULL,
    [source_name]      VARCHAR(200)                  NOT NULL,
    [source_record_id] VARCHAR(500)                  NOT NULL,
    [source_url]       VARCHAR(1000)                 NULL,
    [title]            NVARCHAR(500)                 NULL,
    [body_text]        NVARCHAR(MAX)                 NULL,
    [published_at]     VARCHAR(20)                   NULL,
    [topic]            VARCHAR(100)                  NULL,
    [status]           VARCHAR(50)                   NOT NULL DEFAULT 'pending',
    [created_at]       DATETIME2                     NOT NULL DEFAULT GETDATE(),
    CONSTRAINT PK_article_queue PRIMARY KEY ([id]),
    CONSTRAINT UQ_article_queue UNIQUE ([source_type], [source_name], [source_record_id])
);