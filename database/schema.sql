-- =============================================================================
-- Patient Discharge Planning Coordination Portal with Interdepartmental Logs
-- Database Schema for MySQL 8.0+
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `patient_discharge_db` 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `patient_discharge_db`;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Users Table
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(80) NOT NULL UNIQUE,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(120) NOT NULL,
    `role` VARCHAR(30) NOT NULL,
    `department` VARCHAR(60) NULL,
    `employee_id` VARCHAR(50) NULL,
    `phone` VARCHAR(20) NULL,
    `qualification` VARCHAR(120) NULL,
    `approval_status` VARCHAR(20) NOT NULL DEFAULT 'approved',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `must_change_password` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_approval` (`approval_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Patients Table
DROP TABLE IF EXISTS `patients`;
CREATE TABLE `patients` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` VARCHAR(30) NOT NULL UNIQUE,
    `full_name` VARCHAR(120) NOT NULL,
    `date_of_birth` DATE NOT NULL,
    `gender` VARCHAR(20) NOT NULL,
    `blood_group` VARCHAR(10) NULL,
    `phone` VARCHAR(20) NOT NULL,
    `email` VARCHAR(120) NULL,
    `address` TEXT NULL,
    `emergency_contact_name` VARCHAR(120) NULL,
    `emergency_contact_phone` VARCHAR(20) NULL,
    `user_id` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_patients_id` (`patient_id`),
    INDEX `idx_patients_name` (`full_name`),
    CONSTRAINT `fk_patients_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Rooms Table
DROP TABLE IF EXISTS `rooms`;
CREATE TABLE `rooms` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `room_number` VARCHAR(20) NOT NULL UNIQUE,
    `ward` VARCHAR(60) NOT NULL,
    `room_type` VARCHAR(50) NOT NULL,
    `daily_rate` DECIMAL(10,2) NOT NULL DEFAULT 1500.00,
    `is_occupied` BOOLEAN NOT NULL DEFAULT FALSE,
    `current_patient_id` INT NULL,
    `current_admission_id` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_rooms_patient` FOREIGN KEY (`current_patient_id`) REFERENCES `patients` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Admissions Table
DROP TABLE IF EXISTS `admissions`;
CREATE TABLE `admissions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `admission_number` VARCHAR(30) NOT NULL UNIQUE,
    `patient_id` INT NOT NULL,
    `room_id` INT NOT NULL,
    `admitting_doctor_id` INT NOT NULL,
    `assigned_nurse_id` INT NOT NULL,
    `admission_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `discharge_date` DATETIME NULL,
    `status` VARCHAR(40) NOT NULL DEFAULT 'Admitted',
    `admission_reason` TEXT NOT NULL,
    `initial_diagnosis` TEXT NULL,
    `admission_remarks` TEXT NULL,
    `discharged_by_user_id` INT NULL,
    `discharge_summary` TEXT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_admissions_status` (`status`),
    INDEX `idx_admissions_date` (`admission_date`),
    CONSTRAINT `fk_admissions_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_admissions_room` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`),
    CONSTRAINT `fk_admissions_doctor` FOREIGN KEY (`admitting_doctor_id`) REFERENCES `users` (`id`),
    CONSTRAINT `fk_admissions_nurse` FOREIGN KEY (`assigned_nurse_id`) REFERENCES `users` (`id`),
    CONSTRAINT `fk_admissions_discharger` FOREIGN KEY (`discharged_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Discharge Coordinations Table
DROP TABLE IF EXISTS `discharge_coordinations`;
CREATE TABLE `discharge_coordinations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `admission_id` INT NOT NULL UNIQUE,
    `initiated_by_doctor_id` INT NOT NULL,
    `initiated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `clinical_readiness_approved` BOOLEAN NOT NULL DEFAULT FALSE,
    `clinical_notes` TEXT NULL,
    `follow_up_instructions` TEXT NULL,
    `requires_nursing` BOOLEAN NOT NULL DEFAULT TRUE,
    `requires_pharmacy` BOOLEAN NOT NULL DEFAULT TRUE,
    `requires_laboratory` BOOLEAN NOT NULL DEFAULT FALSE,
    `requires_billing_clearance` BOOLEAN NOT NULL DEFAULT TRUE,
    `nursing_cleared` BOOLEAN NOT NULL DEFAULT FALSE,
    `nursing_cleared_at` DATETIME NULL,
    `nursing_cleared_by_id` INT NULL,
    `pharmacy_cleared` BOOLEAN NOT NULL DEFAULT FALSE,
    `pharmacy_cleared_at` DATETIME NULL,
    `pharmacy_cleared_by_id` INT NULL,
    `laboratory_cleared` BOOLEAN NOT NULL DEFAULT FALSE,
    `laboratory_cleared_at` DATETIME NULL,
    `laboratory_cleared_by_id` INT NULL,
    `billing_cleared` BOOLEAN NOT NULL DEFAULT FALSE,
    `billing_cleared_at` DATETIME NULL,
    `billing_cleared_by_id` INT NULL,
    `is_ready_for_discharge` BOOLEAN NOT NULL DEFAULT FALSE,
    `ready_calculated_at` DATETIME NULL,
    `is_finalized` BOOLEAN NOT NULL DEFAULT FALSE,
    `final_discharged_at` DATETIME NULL,
    `final_discharged_by_id` INT NULL,
    CONSTRAINT `fk_dc_admission` FOREIGN KEY (`admission_id`) REFERENCES `admissions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_dc_doctor` FOREIGN KEY (`initiated_by_doctor_id`) REFERENCES `users` (`id`),
    CONSTRAINT `fk_dc_nurse` FOREIGN KEY (`nursing_cleared_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_dc_pharm` FOREIGN KEY (`pharmacy_cleared_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_dc_lab` FOREIGN KEY (`laboratory_cleared_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_dc_bill` FOREIGN KEY (`billing_cleared_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_dc_finalizer` FOREIGN KEY (`final_discharged_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. Department Tasks Table
DROP TABLE IF EXISTS `department_tasks`;
CREATE TABLE `department_tasks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `task_code` VARCHAR(30) NOT NULL UNIQUE,
    `admission_id` INT NOT NULL,
    `discharge_coordination_id` INT NOT NULL,
    `department` VARCHAR(40) NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'Pending',
    `blocked_reason` TEXT NULL,
    `assigned_to_user_id` INT NULL,
    `completed_by_user_id` INT NULL,
    `completed_at` DATETIME NULL,
    `remarks` TEXT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_tasks_dept` (`department`),
    INDEX `idx_tasks_status` (`status`),
    CONSTRAINT `fk_tasks_admission` FOREIGN KEY (`admission_id`) REFERENCES `admissions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_tasks_dc` FOREIGN KEY (`discharge_coordination_id`) REFERENCES `discharge_coordinations` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_tasks_assigned` FOREIGN KEY (`assigned_to_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_tasks_completed` FOREIGN KEY (`completed_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. Communication Logs Table
DROP TABLE IF EXISTS `communication_logs`;
CREATE TABLE `communication_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL,
    `admission_id` INT NOT NULL,
    `discharge_coordination_id` INT NULL,
    `task_id` INT NULL,
    `sender_id` INT NOT NULL,
    `sender_role` VARCHAR(30) NOT NULL,
    `source_department` VARCHAR(50) NOT NULL,
    `target_department` VARCHAR(50) NOT NULL,
    `message` TEXT NOT NULL,
    `log_type` VARCHAR(30) NOT NULL DEFAULT 'message',
    `is_acknowledged` BOOLEAN NOT NULL DEFAULT FALSE,
    `acknowledged_by_id` INT NULL,
    `acknowledged_at` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_comm_admission` (`admission_id`),
    INDEX `idx_comm_created` (`created_at`),
    CONSTRAINT `fk_comm_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comm_admission` FOREIGN KEY (`admission_id`) REFERENCES `admissions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comm_dc` FOREIGN KEY (`discharge_coordination_id`) REFERENCES `discharge_coordinations` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_comm_task` FOREIGN KEY (`task_id`) REFERENCES `department_tasks` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_comm_sender` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`),
    CONSTRAINT `fk_comm_ack` FOREIGN KEY (`acknowledged_by_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. Notifications Table
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `recipient_user_id` INT NOT NULL,
    `event_type` VARCHAR(60) NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` TEXT NOT NULL,
    `link_url` VARCHAR(255) NULL,
    `is_read` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_notifications_user` (`recipient_user_id`),
    INDEX `idx_notifications_read` (`is_read`),
    CONSTRAINT `fk_notifications_user` FOREIGN KEY (`recipient_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. Billing Accounts Table
DROP TABLE IF EXISTS `billing_accounts`;
CREATE TABLE `billing_accounts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `admission_id` INT NOT NULL UNIQUE,
    `patient_id` INT NOT NULL,
    `total_room_charges` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `total_pharmacy_charges` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `total_lab_charges` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `total_consultation_charges` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `total_nursing_charges` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `total_other_charges` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `subtotal_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `discount_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `total_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `paid_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `balance_due` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    `payment_status` VARCHAR(30) NOT NULL DEFAULT 'Unpaid',
    `is_finalized` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_billing_admission` FOREIGN KEY (`admission_id`) REFERENCES `admissions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_billing_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 10. Billing Items Table
DROP TABLE IF EXISTS `billing_items`;
CREATE TABLE `billing_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `billing_account_id` INT NOT NULL,
    `category` VARCHAR(50) NOT NULL,
    `description` VARCHAR(200) NOT NULL,
    `unit_price` DECIMAL(10,2) NOT NULL,
    `quantity` DECIMAL(8,2) NOT NULL DEFAULT 1.00,
    `total_price` DECIMAL(10,2) NOT NULL,
    `added_by_user_id` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_items_account` (`billing_account_id`),
    CONSTRAINT `fk_items_account` FOREIGN KEY (`billing_account_id`) REFERENCES `billing_accounts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_items_user` FOREIGN KEY (`added_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 11. Payments Table
DROP TABLE IF EXISTS `payments`;
CREATE TABLE `payments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `billing_account_id` INT NOT NULL,
    `payment_reference` VARCHAR(60) NOT NULL UNIQUE,
    `amount` DECIMAL(10,2) NOT NULL,
    `payment_method` VARCHAR(30) NOT NULL,
    `transaction_id` VARCHAR(100) NULL,
    `notes` TEXT NULL,
    `recorded_by_user_id` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_payments_account` (`billing_account_id`),
    CONSTRAINT `fk_payments_account` FOREIGN KEY (`billing_account_id`) REFERENCES `billing_accounts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_payments_user` FOREIGN KEY (`recorded_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 12. Audit Events Table
DROP TABLE IF EXISTS `audit_events`;
CREATE TABLE `audit_events` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `action` VARCHAR(80) NOT NULL,
    `entity_type` VARCHAR(50) NOT NULL,
    `entity_id` VARCHAR(50) NULL,
    `details` TEXT NULL,
    `ip_address` VARCHAR(45) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_audit_action` (`action`),
    CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
