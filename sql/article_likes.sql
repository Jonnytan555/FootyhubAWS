CREATE TABLE dbo.article_likes (
    user_id    INT NOT NULL,
    article_id INT NOT NULL,
    PRIMARY KEY (user_id, article_id)
);