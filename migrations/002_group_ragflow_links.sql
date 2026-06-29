-- Persist Ragflow dataset/chat IDs linked to Criadex index groups.
CREATE TABLE IF NOT EXISTS `GroupRagflowLinks` (
    `group_name` VARCHAR(255) NOT NULL,
    `ragflow_dataset_id` VARCHAR(64) NOT NULL,
    `ragflow_dataset_name` VARCHAR(128) NOT NULL,
    `ragflow_chat_id` VARCHAR(64) NULL,
    `updated_at` BIGINT NOT NULL,
    PRIMARY KEY (`group_name`),
    INDEX `idx_ragflow_dataset_id` (`ragflow_dataset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
