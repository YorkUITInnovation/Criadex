-- Migration: Drop legacy Groups model foreign keys (allow generic model IDs)
-- Safe on fresh installs where constraints were never created.

SET @db = DATABASE();

SET @sql = IF(
    (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
     WHERE CONSTRAINT_SCHEMA = @db AND TABLE_NAME = 'Groups'
     AND CONSTRAINT_NAME = 'groups_ibfk_1' AND CONSTRAINT_TYPE = 'FOREIGN KEY') > 0,
    'ALTER TABLE `Groups` DROP FOREIGN KEY `groups_ibfk_1`',
    'SELECT 1'
);
PREPARE s1 FROM @sql;
EXECUTE s1;
DEALLOCATE PREPARE s1;

SET @sql = IF(
    (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
     WHERE CONSTRAINT_SCHEMA = @db AND TABLE_NAME = 'Groups'
     AND CONSTRAINT_NAME = 'groups_ibfk_2' AND CONSTRAINT_TYPE = 'FOREIGN KEY') > 0,
    'ALTER TABLE `Groups` DROP FOREIGN KEY `groups_ibfk_2`',
    'SELECT 1'
);
PREPARE s2 FROM @sql;
EXECUTE s2;
DEALLOCATE PREPARE s2;

SET @sql = IF(
    (SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
     WHERE CONSTRAINT_SCHEMA = @db AND TABLE_NAME = 'Groups'
     AND CONSTRAINT_NAME = 'groups_ibfk_3' AND CONSTRAINT_TYPE = 'FOREIGN KEY') > 0,
    'ALTER TABLE `Groups` DROP FOREIGN KEY `groups_ibfk_3`',
    'SELECT 1'
);
PREPARE s3 FROM @sql;
EXECUTE s3;
DEALLOCATE PREPARE s3;
