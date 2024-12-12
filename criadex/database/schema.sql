USE criadex;


CREATE TABLE IF NOT EXISTS `AzureModels`
(
    `id`             INT AUTO_INCREMENT PRIMARY KEY,
    `api_resource`   VARCHAR(128) NOT NULL,
    `api_version`    VARCHAR(128) NOT NULL,
    `api_key`        VARCHAR(128) NOT NULL,
    `api_deployment` VARCHAR(128) NOT NULL,
    `api_model`      VARCHAR(128) NOT NULL,
    UNIQUE (`api_resource`, `api_deployment`)
);

CREATE TABLE IF NOT EXISTS `CohereModels`
(
    `id`        INT AUTO_INCREMENT PRIMARY KEY,
    `api_model` VARCHAR(128) NOT NULL,
    `api_key`   VARCHAR(128) NOT NULL,
    UNIQUE (`api_key`, `api_model`)
);

CREATE TABLE IF NOT EXISTS `Groups`
(
    `id`                 INT AUTO_INCREMENT PRIMARY KEY,
    `name`               VARCHAR(128) NOT NULL UNIQUE,
    `type`               TINYINT      NOT NULL,
    `created`            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `llm_model_id`       INT          NOT NULL,
    `embedding_model_id` INT          NOT NULL,
    `rerank_model_id`    INT          NOT NULL,
    UNIQUE (`name`),
    FOREIGN KEY (llm_model_id) REFERENCES AzureModels (id),
    FOREIGN KEY (embedding_model_id) REFERENCES AzureModels (id),
    FOREIGN KEY (rerank_model_id) REFERENCES CohereModels (id)
);

CREATE TABLE IF NOT EXISTS `Documents`
(
    `id`       INT AUTO_INCREMENT PRIMARY KEY,
    `name`     VARCHAR(128) NOT NULL,
    `group_id` INT          NOT NULL,
    `created`  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (`name`, `group_id`),
    FOREIGN KEY (group_id) REFERENCES `Groups` (id)
);

CREATE TABLE IF NOT EXISTS `Assets`
(
    `id`          INT AUTO_INCREMENT PRIMARY KEY,
    `uuid`        BINARY(16)  NOT NULL,
    `document_id` INT          NOT NULL,
    `group_id`    INT          NOT NULL,
    `mimetype`    VARCHAR(128) NOT NULL,
    `data`        LONGBLOB     NOT NULL,
    `created`     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (`uuid`, `document_id`),
    FOREIGN KEY (document_id) REFERENCES `Documents` (id),
    FOREIGN KEY (group_id) REFERENCES `Groups` (id)
);

