


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
    `rerank_model_id`    INT          NOT NULL
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
    `uuid`        BINARY(16)   NOT NULL,
    `document_id` INT          NOT NULL,
    `group_id`    INT          NOT NULL,
    `mimetype`    VARCHAR(128) NOT NULL,
    `data`        LONGBLOB     NOT NULL,
    `created`     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (`uuid`, `document_id`),
    FOREIGN KEY (document_id) REFERENCES `Documents` (id),
    FOREIGN KEY (group_id) REFERENCES `Groups` (id)
);

CREATE TABLE IF NOT EXISTS `GenericModels`
(
    `id`            INT AUTO_INCREMENT PRIMARY KEY,
    `provider_type` VARCHAR(64)  NOT NULL,
    `config`        JSON         NOT NULL,
    `created`       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `GroupGraphStates`
(
    `group_name`      VARCHAR(128) NOT NULL PRIMARY KEY,
    `status`          VARCHAR(32)  NOT NULL DEFAULT 'NOT_BUILT',
    `source`          VARCHAR(32)  NOT NULL DEFAULT 'none',
    `node_count`      INT          NOT NULL DEFAULT 0,
    `edge_count`      INT          NOT NULL DEFAULT 0,
    `top_entities`    JSON         NULL,
    `fallback_reason` TEXT         NULL,
    `error`           TEXT         NULL,
    `built_at`        BIGINT       NULL,
    `updated_at`      BIGINT       NOT NULL,
    INDEX `idx_group_graph_status` (`status`)
);

CREATE TABLE IF NOT EXISTS `GraphBuildJobs`
(
    `job_id`          VARCHAR(64)  NOT NULL PRIMARY KEY,
    `group_name`      VARCHAR(128) NOT NULL,
    `state`           VARCHAR(32)  NOT NULL,
    `source`          VARCHAR(32)  NULL,
    `progress`        INT          NOT NULL DEFAULT 0,
    `error`           TEXT         NULL,
    `metadata`        JSON         NULL,
    `created_at`      BIGINT       NOT NULL,
    `updated_at`      BIGINT       NOT NULL,
    `started_at`      BIGINT       NULL,
    `finished_at`     BIGINT       NULL,
    INDEX `idx_graph_jobs_group` (`group_name`),
    INDEX `idx_graph_jobs_state` (`state`)
);
