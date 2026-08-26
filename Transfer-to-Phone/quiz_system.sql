-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: quiz_system
-- ------------------------------------------------------
-- Server version	10.4.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `quiz_system`
--

/*!40000 DROP DATABASE IF EXISTS `quiz_system`*/;

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `quiz_system` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;

USE `quiz_system`;

--
-- Table structure for table `activity_logs`
--

DROP TABLE IF EXISTS `activity_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `activity_logs` (
  `log_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `action` varchar(50) NOT NULL,
  `description` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`log_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `activity_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=146 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activity_logs`
--

LOCK TABLES `activity_logs` WRITE;
/*!40000 ALTER TABLE `activity_logs` DISABLE KEYS */;
INSERT INTO `activity_logs` VALUES (1,4,'LOGIN','Logged in as STUDENT.','2026-07-26 17:41:17'),(2,4,'LOGIN','Logged in as STUDENT.','2026-07-26 17:41:55'),(3,4,'LOGIN','Logged in as STUDENT.','2026-07-26 17:42:19'),(4,4,'LOGIN','Logged in as STUDENT.','2026-07-26 17:42:49'),(5,4,'LOGIN','Logged in as STUDENT.','2026-07-26 17:43:20'),(6,4,'LOGIN','Logged in as STUDENT.','2026-07-26 18:09:59'),(7,4,'LOGIN','Logged in as STUDENT.','2026-07-26 18:12:34'),(8,4,'LOGIN','Logged in as STUDENT.','2026-07-26 18:13:28'),(9,4,'LOGIN','Logged in as STUDENT.','2026-07-26 18:46:48'),(10,4,'LOGIN','Logged in as STUDENT.','2026-07-26 18:47:12'),(11,4,'LOGIN','Logged in as STUDENT.','2026-07-27 03:01:34'),(12,4,'LOGIN','Logged in as STUDENT.','2026-07-27 03:12:57'),(13,1,'LOGIN','Logged in as TEACHER.','2026-07-27 20:12:19'),(14,1,'LOGIN','Logged in as TEACHER.','2026-07-27 20:16:58'),(15,1,'LOGIN','Logged in as TEACHER.','2026-07-27 20:26:05'),(16,1,'LOGIN','Logged in as TEACHER.','2026-07-27 20:40:09'),(17,1,'LOGIN','Logged in as TEACHER.','2026-07-27 20:45:24'),(18,1,'LOGIN','Logged in as TEACHER.','2026-07-27 20:50:37'),(19,1,'LOGIN','Logged in as TEACHER.','2026-07-27 20:57:25'),(20,4,'LOGIN','Logged in as STUDENT.','2026-07-27 21:10:58'),(21,4,'LOGIN','Logged in as STUDENT.','2026-07-27 21:34:06'),(22,4,'LOGIN','Logged in as STUDENT.','2026-07-27 21:34:33'),(23,1,'LOGIN','Logged in as TEACHER.','2026-07-28 02:40:32'),(24,4,'LOGIN','Logged in as STUDENT.','2026-07-28 02:42:03'),(25,1,'LOGIN','Logged in as TEACHER.','2026-07-28 02:52:34'),(26,4,'LOGIN','Logged in as STUDENT.','2026-07-28 03:59:56'),(27,4,'LOGIN','Logged in as STUDENT.','2026-07-28 04:23:24'),(28,1,'LOGIN','Logged in as TEACHER.','2026-07-28 05:40:47'),(29,4,'LOGIN','Logged in as STUDENT.','2026-07-28 06:20:47'),(30,4,'LOGIN','Logged in as STUDENT.','2026-07-28 07:36:46'),(31,4,'LOGIN','Logged in as STUDENT.','2026-07-28 10:02:05'),(32,1,'LOGIN','Logged in as TEACHER.','2026-07-28 10:06:07'),(33,4,'LOGIN','Logged in as STUDENT.','2026-07-28 10:32:52'),(34,1,'LOGIN','Logged in as TEACHER.','2026-07-28 10:50:53'),(35,4,'LOGIN','Logged in as STUDENT.','2026-07-28 14:57:39'),(36,4,'LOGIN','Logged in as STUDENT.','2026-07-28 14:58:48'),(37,1,'LOGIN','Logged in as TEACHER.','2026-07-28 15:19:26'),(38,1,'LOGIN','Logged in as TEACHER.','2026-07-29 17:25:50'),(39,1,'LOGIN','Logged in as TEACHER.','2026-07-29 17:26:05'),(40,1,'LOGIN','Logged in as TEACHER.','2026-07-29 17:26:27'),(41,1,'LOGIN','Logged in as TEACHER.','2026-07-29 17:26:42'),(42,1,'LOGIN','Logged in as TEACHER.','2026-07-29 17:27:18'),(43,1,'LOGIN','Logged in as TEACHER.','2026-07-29 17:27:58'),(44,4,'LOGIN','Logged in as STUDENT.','2026-07-30 02:13:00'),(45,1,'LOGIN','Logged in as TEACHER.','2026-07-30 02:14:14'),(46,4,'LOGIN','Logged in as STUDENT.','2026-07-30 02:22:24'),(47,1,'LOGIN','Logged in as TEACHER.','2026-07-30 02:29:15'),(48,4,'LOGIN','Logged in as STUDENT.','2026-07-30 08:40:41'),(49,1,'LOGIN','Logged in as TEACHER.','2026-07-31 15:30:11'),(50,1,'LOGIN','Logged in as TEACHER.','2026-07-31 15:32:08'),(51,1,'LOGIN','Logged in as TEACHER.','2026-07-31 15:32:13'),(52,1,'LOGIN','Logged in as TEACHER.','2026-07-31 15:32:19'),(53,2,'LOGIN','Logged in as TEACHER.','2026-07-31 15:32:24'),(54,4,'LOGIN','Logged in as STUDENT.','2026-07-31 15:32:25'),(55,4,'LOGIN','Logged in as STUDENT.','2026-07-31 15:33:05'),(56,4,'LOGIN','Logged in as STUDENT.','2026-07-31 15:33:24'),(57,4,'LOGIN','Logged in as STUDENT.','2026-07-31 15:33:53'),(58,4,'LOGIN','Logged in as STUDENT.','2026-07-31 15:34:08'),(59,4,'LOGIN','Logged in as STUDENT.','2026-07-31 15:34:24'),(60,4,'LOGIN','Logged in as STUDENT.','2026-07-31 15:39:52'),(61,1,'LOGIN','Logged in as TEACHER.','2026-07-31 15:40:07'),(62,4,'LOGIN','Logged in as STUDENT.','2026-07-31 15:45:29'),(63,1,'LOGIN','Logged in as TEACHER.','2026-07-31 15:51:24'),(64,4,'LOGIN','Logged in as STUDENT.','2026-07-31 16:02:12'),(65,1,'LOGIN','Logged in as TEACHER.','2026-07-31 16:11:33'),(66,4,'LOGIN','Logged in as STUDENT.','2026-07-31 16:11:38'),(67,4,'LOGIN','Logged in as STUDENT.','2026-07-31 16:11:46'),(68,4,'LOGIN','Logged in as STUDENT.','2026-07-31 16:13:01'),(69,1,'LOGIN','Logged in as TEACHER.','2026-07-31 16:16:25'),(70,1,'LOGIN','Logged in as TEACHER.','2026-07-31 16:34:43'),(71,1,'LOGIN','Logged in as TEACHER.','2026-07-31 16:34:48'),(72,1,'LOGIN','Logged in as TEACHER.','2026-07-31 16:34:52'),(73,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:03:48'),(74,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:04:02'),(75,4,'LOGIN','Logged in as STUDENT.','2026-07-31 17:04:09'),(76,4,'LOGIN','Logged in as STUDENT.','2026-07-31 17:04:15'),(77,5,'LOGIN','Logged in as STUDENT.','2026-07-31 17:04:34'),(78,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:13:24'),(79,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:28:29'),(80,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:45:46'),(81,4,'LOGIN','Logged in as STUDENT.','2026-07-31 17:45:47'),(82,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:45:56'),(83,5,'LOGIN','Logged in as STUDENT.','2026-07-31 17:45:56'),(84,4,'LOGIN','Logged in as STUDENT.','2026-07-31 17:47:12'),(85,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:47:51'),(86,4,'LOGIN','Logged in as STUDENT.','2026-07-31 17:49:26'),(87,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:50:03'),(88,4,'LOGIN','Logged in as STUDENT.','2026-07-31 17:51:28'),(89,1,'LOGIN','Logged in as TEACHER.','2026-07-31 17:51:47'),(90,4,'LOGIN','Logged in as STUDENT.','2026-07-31 18:01:14'),(91,1,'LOGIN','Logged in as TEACHER.','2026-07-31 18:01:39'),(92,4,'LOGIN','Logged in as STUDENT.','2026-07-31 18:09:45'),(93,1,'LOGIN','Logged in as TEACHER.','2026-07-31 18:10:38'),(94,1,'LOGIN','Logged in as TEACHER.','2026-07-31 18:10:43'),(95,4,'LOGIN','Logged in as STUDENT.','2026-08-01 00:29:33'),(96,1,'LOGIN','Logged in as TEACHER.','2026-08-01 00:30:01'),(97,4,'LOGIN','Logged in as STUDENT.','2026-08-01 00:35:10'),(98,1,'LOGIN','Logged in as TEACHER.','2026-08-01 00:41:30'),(99,4,'LOGIN','Logged in as STUDENT.','2026-08-01 00:45:24'),(100,4,'LOGIN','Logged in as STUDENT.','2026-08-01 00:45:34'),(101,1,'LOGIN','Logged in as TEACHER.','2026-08-01 00:46:55'),(102,4,'LOGIN','Logged in as STUDENT.','2026-08-01 00:49:36'),(103,1,'LOGIN','Logged in as TEACHER.','2026-08-01 00:56:38'),(104,4,'LOGIN','Logged in as STUDENT.','2026-08-01 00:57:51'),(105,4,'LOGIN','Logged in as STUDENT.','2026-08-01 00:58:19'),(106,1,'LOGIN','Logged in as TEACHER.','2026-08-01 00:58:35'),(107,4,'LOGIN','Logged in as STUDENT.','2026-08-01 01:00:43'),(108,1,'LOGIN','Logged in as TEACHER.','2026-08-01 01:03:09'),(109,4,'LOGIN','Logged in as STUDENT.','2026-08-01 01:07:05'),(110,1,'LOGIN','Logged in as TEACHER.','2026-08-01 01:08:31'),(111,4,'LOGIN','Logged in as STUDENT.','2026-08-01 01:59:41'),(112,1,'LOGIN','Logged in as TEACHER.','2026-08-01 02:00:32'),(113,4,'LOGIN','Logged in as STUDENT.','2026-08-01 02:04:42'),(114,1,'LOGIN','Logged in as TEACHER.','2026-08-13 07:35:21'),(115,4,'LOGIN','Logged in as STUDENT.','2026-08-15 01:24:22'),(116,1,'LOGIN','Logged in as TEACHER.','2026-08-15 01:37:08'),(117,5,'LOGIN','Logged in as STUDENT.','2026-08-15 01:40:08'),(118,4,'LOGIN','Logged in as STUDENT.','2026-08-15 01:40:44'),(119,6,'LOGIN','Logged in as STUDENT.','2026-08-15 01:41:26'),(120,6,'LOGIN','Logged in as STUDENT.','2026-08-15 01:41:42'),(121,6,'LOGIN','Logged in as STUDENT.','2026-08-15 01:42:14'),(122,6,'LOGIN','Logged in as STUDENT.','2026-08-15 01:42:24'),(123,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:03:30'),(124,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:03:44'),(125,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:03:44'),(126,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:04:25'),(127,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:04:48'),(128,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:04:56'),(129,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:06:49'),(130,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:07:57'),(131,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:08:07'),(132,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:09:42'),(133,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:09:54'),(134,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:10:06'),(135,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:10:11'),(136,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:12:09'),(137,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:14:29'),(138,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:24:27'),(139,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:25:11'),(140,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:30:33'),(141,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:33:26'),(142,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:35:06'),(143,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:35:22'),(144,4,'LOGIN','Logged in as STUDENT.','2026-08-15 02:36:10'),(145,1,'LOGIN','Logged in as TEACHER.','2026-08-15 02:37:48');
/*!40000 ALTER TABLE `activity_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `classes`
--

DROP TABLE IF EXISTS `classes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `classes` (
  `class_id` int(11) NOT NULL AUTO_INCREMENT,
  `subject_code` varchar(20) NOT NULL,
  `subject_name` varchar(150) NOT NULL,
  `block` varchar(50) NOT NULL,
  `class_code` varchar(10) NOT NULL,
  `teacher_id` int(11) NOT NULL,
  `status` enum('ACTIVE','ARCHIVED') DEFAULT 'ACTIVE',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`class_id`),
  UNIQUE KEY `class_code` (`class_code`),
  KEY `teacher_id` (`teacher_id`),
  CONSTRAINT `classes_ibfk_1` FOREIGN KEY (`teacher_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `classes`
--

LOCK TABLES `classes` WRITE;
/*!40000 ALTER TABLE `classes` DISABLE KEYS */;
INSERT INTO `classes` VALUES (1,'IT 301','Software Engineering','BSIT 3-A','7F3K9Q',1,'ACTIVE','2026-07-26 17:40:34'),(2,'IT 302','Database Systems','BSIT 3-A','8G2M4P',2,'ACTIVE','2026-07-26 17:40:34'),(3,'IT 303','Web Development','BSIT 3-A','2H5N7R',3,'ACTIVE','2026-07-26 17:40:34'),(4,'IT 201','Data Structures','BSIT 2-B','9K3L6T',2,'ACTIVE','2026-07-26 17:40:34'),(5,'it124','intro to computing','block-1','A23523',1,'ACTIVE','2026-07-28 10:10:38'),(6,'THSS2','CS THESIS 2','Block 2','E87769',1,'ACTIVE','2026-07-30 02:11:33'),(7,'CC121','PROGRAMMING 1','BLOCK 1','9D5C2C',1,'ACTIVE','2026-07-31 17:49:04');
/*!40000 ALTER TABLE `classes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `enrollments`
--

DROP TABLE IF EXISTS `enrollments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `enrollments` (
  `enrollment_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `class_id` int(11) NOT NULL,
  `enrolled_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`enrollment_id`),
  UNIQUE KEY `unique_enrollment` (`user_id`,`class_id`),
  KEY `idx_enrollments_user` (`user_id`),
  KEY `idx_enrollments_class` (`class_id`),
  CONSTRAINT `enrollments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `enrollments_ibfk_2` FOREIGN KEY (`class_id`) REFERENCES `classes` (`class_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `enrollments`
--

LOCK TABLES `enrollments` WRITE;
/*!40000 ALTER TABLE `enrollments` DISABLE KEYS */;
INSERT INTO `enrollments` VALUES (1,4,1,'2026-07-26 17:40:34'),(2,4,2,'2026-07-26 17:40:34'),(3,4,3,'2026-07-26 17:40:34'),(4,5,1,'2026-07-26 17:40:34'),(5,5,2,'2026-07-26 17:40:34'),(6,6,4,'2026-07-26 17:40:34'),(7,4,4,'2026-07-26 17:43:20'),(8,4,5,'2026-07-28 10:33:47'),(9,4,6,'2026-07-30 02:13:04'),(10,4,7,'2026-07-31 17:49:42');
/*!40000 ALTER TABLE `enrollments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exam_proctoring_log`
--

DROP TABLE IF EXISTS `exam_proctoring_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exam_proctoring_log` (
  `log_id` int(11) NOT NULL AUTO_INCREMENT,
  `exam_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `event_type` varchar(30) NOT NULL DEFAULT 'TAB_SWITCH',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`log_id`),
  KEY `idx_proc_exam_user` (`exam_id`,`user_id`),
  KEY `idx_proc_created` (`exam_id`,`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exam_proctoring_log`
--

LOCK TABLES `exam_proctoring_log` WRITE;
/*!40000 ALTER TABLE `exam_proctoring_log` DISABLE KEYS */;
INSERT INTO `exam_proctoring_log` VALUES (3,15,4,'TAB_SWITCH','2026-08-01 09:02:24'),(4,15,4,'TAB_SWITCH','2026-08-01 09:02:44'),(5,15,4,'TAB_SWITCH','2026-08-01 09:02:47'),(6,15,4,'TAB_SWITCH','2026-08-01 09:02:51'),(7,19,4,'TAB_SWITCH','2026-08-15 10:36:59'),(8,19,4,'TAB_SWITCH','2026-08-15 10:37:04'),(9,19,4,'TAB_SWITCH','2026-08-15 10:37:07'),(10,19,4,'TAB_SWITCH','2026-08-15 10:37:10');
/*!40000 ALTER TABLE `exam_proctoring_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exam_submissions`
--

DROP TABLE IF EXISTS `exam_submissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exam_submissions` (
  `submission_id` int(11) NOT NULL AUTO_INCREMENT,
  `exam_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `answers_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`answers_json`)),
  `score` int(11) DEFAULT NULL,
  `correct_count` int(11) DEFAULT NULL,
  `total_questions` int(11) DEFAULT NULL,
  `time_used_secs` int(11) DEFAULT NULL,
  `exit_attempts` int(11) DEFAULT 0,
  `auto_submitted` tinyint(1) DEFAULT 0,
  `submitted_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`submission_id`),
  UNIQUE KEY `unique_submission` (`exam_id`,`user_id`),
  KEY `idx_submissions_user` (`user_id`),
  KEY `idx_submissions_exam` (`exam_id`),
  CONSTRAINT `exam_submissions_ibfk_1` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`exam_id`) ON DELETE CASCADE,
  CONSTRAINT `exam_submissions_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exam_submissions`
--

LOCK TABLES `exam_submissions` WRITE;
/*!40000 ALTER TABLE `exam_submissions` DISABLE KEYS */;
INSERT INTO `exam_submissions` VALUES (1,3,4,'{\"16\":\"Hyper Text Markup Language\",\"17\":\"color\",\"18\":\"<a>\",\"19\":\"Width, height, depth\",\"20\":\"getElementById()\"}',80,4,5,3600,0,0,'2026-07-26 17:40:34'),(2,1,4,'{\"1\":\"A\",\"2\":\"B\",\"3\":\"C\",\"4\":\"B\",\"5\":\"C\",\"6\":\"C\",\"7\":\"B\",\"8\":\"B\",\"9\":\"B\",\"10\":\"C\"}',100,10,10,1200,0,0,'2026-07-26 17:42:19'),(3,4,4,'{\"16\":\"B\",\"17\":\"A\",\"18\":\"B\",\"19\":\"C\",\"20\":\"B\"}',0,0,5,600,0,0,'2026-07-26 17:42:49'),(4,6,4,'{\"32\":\"diet\",\"33\":\"Rodrigo Sanchez \",\"34\":\"yes\",\"35\":\"idk bruh\",\"31\":\"go die\"}',0,0,6,65,0,0,'2026-07-28 06:22:18'),(5,7,4,'{\"37\":\"kwnans\",\"38\":\"jnmsasz\",\"39\":\"make ur bloodd\",\"40\":\"ksimwkss\",\"41\":\"O(n)\",\"42\":\"Stack\",\"43\":\"Standard Query Language\"}',20,2,9,50,0,0,'2026-07-28 10:35:21'),(6,8,4,'{\"48\":\"heha\",\"46\":\"my name is arnel\",\"47\":\"hehe\"}',25,1,4,99,0,0,'2026-07-30 02:24:54'),(7,9,4,'{\"50\":\"O(n)\",\"51\":\"Stack\",\"52\":\"Structured Query Language\",\"53\":\"Hiding implementation details\"}',80,4,5,20,0,0,'2026-07-31 18:10:20'),(9,11,4,'{\"56\":\"\",\"57\":\"\",\"58\":\"\",\"59\":\"\",\"60\":\"\"}',0,0,5,183,0,0,'2026-08-01 00:38:41'),(11,12,4,'[]',0,0,5,0,0,0,'2026-08-01 00:45:50'),(12,14,4,'[]',0,0,5,0,0,0,'2026-08-01 00:49:46'),(13,13,4,'[]',0,0,5,0,0,0,'2026-08-01 00:50:06'),(14,15,4,'{\"76\":\"O(n)\",\"77\":\"Stack\",\"78\":\"Structured Query Language\"}',60,3,5,112,4,0,'2026-08-01 01:02:56'),(15,16,4,'{\"81\":\"Au\",\"82\":\"Au\",\"84\":\"False\",\"85\":\"True\"}',80,4,5,48,0,0,'2026-08-01 02:05:55'),(16,6,5,'{\"34\":\"True\",\"31\":\"diet\",\"35\":\"wrong answer\",\"32\":\"go die\",\"36\":\"uncle dags\",\"33\":\"Rodrigo Reyes\"}',67,4,6,300,0,0,'2026-08-15 01:40:27'),(20,18,4,'{\"87\":\"O(n)\",\"88\":\"Stack\",\"89\":\"Structured Query Language\",\"90\":\"Hiding implementation details\",\"91\":\"SSH\"}',80,4,5,26,0,0,'2026-08-15 02:31:14'),(21,19,4,'[]',0,0,5,47,4,0,'2026-08-15 02:37:38');
/*!40000 ALTER TABLE `exam_submissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exam_temp_answers`
--

DROP TABLE IF EXISTS `exam_temp_answers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exam_temp_answers` (
  `temp_id` int(11) NOT NULL AUTO_INCREMENT,
  `exam_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `answers_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`answers_json`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`temp_id`),
  UNIQUE KEY `unique_temp_answer` (`exam_id`,`user_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `exam_temp_answers_ibfk_1` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`exam_id`) ON DELETE CASCADE,
  CONSTRAINT `exam_temp_answers_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exam_temp_answers`
--

LOCK TABLES `exam_temp_answers` WRITE;
/*!40000 ALTER TABLE `exam_temp_answers` DISABLE KEYS */;
INSERT INTO `exam_temp_answers` VALUES (1,6,4,'{\"31\":\"go die\",\"32\":\"diet\",\"33\":\"Rodrigo Sanchez \",\"34\":\"yes\",\"35\":\"idk bruh\"}','2026-07-28 06:21:02','2026-07-28 06:22:05'),(2,7,4,'{\"37\":\"kwnans\",\"38\":\"jnmsasz\",\"39\":\"make ur bloodd\",\"40\":\"ksimwkss\",\"41\":\"O(n)\",\"42\":\"Stack\",\"43\":\"Standard Query Language\",\"44\":\"Hiding implementation details\"}','2026-07-28 10:34:03','2026-07-28 10:34:42'),(3,8,4,'{\"46\":\"my name is arnel\",\"47\":\"hehe\",\"48\":\"heha\"}','2026-07-30 02:23:50','2026-07-30 02:24:42'),(4,9,4,'{\"50\":\"O(n)\",\"51\":\"Stack\",\"52\":\"Structured Query Language\",\"53\":\"Hiding implementation details\"}','2026-07-31 18:10:01','2026-07-31 18:10:14'),(5,11,4,'{\"56\":\"oo\",\"57\":\"True\",\"58\":\"Justin\",\"59\":\"-sa dito\\n-sa doon\\n-sa anes \\n-sa dine\",\"60\":\"True\"}','2026-08-01 00:35:46','2026-08-01 00:36:45'),(6,15,4,'{\"76\":\"O(n)\",\"77\":\"Stack\",\"78\":\"Structured Query Language\",\"79\":\"Hiding implementation details\",\"80\":\"FTP\"}','2026-08-01 01:01:04','2026-08-01 01:01:48'),(8,16,4,'{\"81\":\"Au\",\"82\":\"Au\",\"84\":\"False\",\"85\":\"True\"}','2026-08-01 02:05:11','2026-08-01 02:05:36'),(9,18,4,'{\"87\":\"O(n)\",\"88\":\"Stack\",\"89\":\"Structured Query Language\",\"90\":\"Hiding implementation details\",\"91\":\"SSH\"}','2026-08-15 02:30:46','2026-08-15 02:30:58');
/*!40000 ALTER TABLE `exam_temp_answers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exams`
--

DROP TABLE IF EXISTS `exams`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exams` (
  `exam_id` int(11) NOT NULL AUTO_INCREMENT,
  `class_id` int(11) NOT NULL,
  `exam_name` varchar(150) NOT NULL,
  `description` text DEFAULT NULL,
  `duration_minutes` int(11) NOT NULL DEFAULT 60,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `is_closed` tinyint(1) NOT NULL DEFAULT 0,
  `closed_at` datetime DEFAULT NULL,
  `passing_score` int(11) DEFAULT 70,
  `status` enum('DRAFT','SCHEDULED','LIVE','CLOSED','ARCHIVED') NOT NULL DEFAULT 'DRAFT',
  `total_points` int(11) NOT NULL DEFAULT 100,
  `randomize_questions` tinyint(1) DEFAULT 0,
  `randomize_options` tinyint(1) DEFAULT 0,
  `max_exit_attempts` int(11) DEFAULT 3,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`exam_id`),
  KEY `idx_exams_class` (`class_id`),
  CONSTRAINT `exams_ibfk_1` FOREIGN KEY (`class_id`) REFERENCES `classes` (`class_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exams`
--

LOCK TABLES `exams` WRITE;
/*!40000 ALTER TABLE `exams` DISABLE KEYS */;
INSERT INTO `exams` VALUES (1,1,'Midterm Exam','Covers SDLC, Agile, and requirements gathering.',60,'2026-07-26 10:40:34','2026-07-26 11:40:34',1,'2026-07-31 23:34:08',70,'CLOSED',100,0,0,3,'2026-07-26 17:40:34'),(2,2,'Quiz 1','Covers relational database basics and ER modeling.',30,'2026-07-26 10:40:34','2026-07-26 11:10:34',0,NULL,70,'DRAFT',50,0,0,3,'2026-07-26 17:40:34'),(3,3,'Prelim Exam','Covers HTML, CSS, and JavaScript fundamentals.',90,'2026-07-26 10:40:34','2026-07-26 12:10:34',1,'2026-07-31 23:32:25',70,'CLOSED',100,0,0,3,'2026-07-26 17:40:34'),(4,1,'Quiz 1','Covers Software Development Life Cycle models.',30,'2026-07-26 10:40:34','2026-07-26 11:10:34',1,'2026-07-31 23:32:19',70,'CLOSED',50,0,0,3,'2026-07-26 17:40:34'),(5,4,'Midterm Exam','Covers arrays, linked lists, and trees.',60,'2026-07-26 10:40:34','2026-07-26 11:40:34',1,'2026-08-01 01:03:48',70,'CLOSED',100,0,0,3,'2026-07-26 17:40:34'),(6,1,'Quiz 2','',0,'2026-07-27 14:06:23','2026-08-15 23:59:59',0,NULL,50,'LIVE',100,0,0,3,'2026-07-27 21:06:23'),(7,5,'Quiz 1','',0,'2026-07-28 03:32:14','2026-07-28 03:32:14',1,'2026-07-31 23:34:08',50,'CLOSED',100,0,0,3,'2026-07-28 10:32:14'),(8,6,'prrtest lng','',30,'2026-07-29 19:22:02','2026-07-29 19:52:02',1,'2026-07-31 23:34:08',75,'ARCHIVED',100,0,0,3,'2026-07-30 02:22:02'),(9,7,'Prelim Exqm','',60,'2026-08-01 02:09:30','2026-08-01 03:09:30',1,'2026-08-01 08:22:33',70,'CLOSED',100,0,0,3,'2026-07-31 17:51:02'),(11,7,'Eme Eme Quiz 2','',15,'2026-08-01 08:34:36','2026-08-01 08:49:36',1,'2026-08-01 08:49:38',75,'CLOSED',100,0,0,3,'2026-08-01 00:34:36'),(12,7,'PRELIM','',15,'2026-08-01 08:47:22','2026-08-01 09:02:22',1,'2026-08-01 08:47:25',75,'CLOSED',100,0,0,3,'2026-08-01 00:44:25'),(13,7,'PRELIM','',60,'2026-08-01 08:47:54','2026-08-01 09:47:54',1,'2026-08-01 09:59:48',75,'CLOSED',100,0,0,3,'2026-08-01 00:47:54'),(14,7,'PRELIM 2','',45,'2026-08-01 08:49:00','2026-08-01 09:34:00',1,'2026-08-01 08:59:53',75,'CLOSED',100,0,0,3,'2026-08-01 00:49:00'),(15,7,'Midterm','',0,'2026-08-01 09:00:27',NULL,0,NULL,75,'LIVE',100,0,0,3,'2026-08-01 01:00:27'),(16,7,'Prelim','',60,'2026-08-13 16:14:11','2026-08-13 17:14:11',1,'2026-08-15 09:23:05',75,'CLOSED',100,0,0,3,'2026-08-01 02:04:19'),(18,7,'Quiz2','',0,'2026-08-15 10:30:20',NULL,0,NULL,75,'LIVE',100,0,0,3,'2026-08-15 02:30:20'),(19,7,'Quiz 3','',0,'2026-08-15 10:35:56',NULL,0,NULL,75,'LIVE',100,0,0,3,'2026-08-15 02:35:56');
/*!40000 ALTER TABLE `exams` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `password_resets`
--

DROP TABLE IF EXISTS `password_resets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `password_resets` (
  `reset_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `reset_token` varchar(64) NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`reset_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `password_resets_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `password_resets`
--

LOCK TABLES `password_resets` WRITE;
/*!40000 ALTER TABLE `password_resets` DISABLE KEYS */;
/*!40000 ALTER TABLE `password_resets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `questions`
--

DROP TABLE IF EXISTS `questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `questions` (
  `question_id` int(11) NOT NULL AUTO_INCREMENT,
  `exam_id` int(11) NOT NULL,
  `question_text` text NOT NULL,
  `question_type` enum('MULTIPLE_CHOICE','TRUE_FALSE','IDENTIFICATION','ENUMERATION') DEFAULT 'MULTIPLE_CHOICE',
  `options` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`options`)),
  `correct_answer` varchar(500) DEFAULT NULL,
  `points` int(11) DEFAULT 1,
  `answer_matching` enum('EXACT','IGNORE_CASE') DEFAULT 'EXACT',
  `option_a` varchar(255) NOT NULL,
  `option_b` varchar(255) NOT NULL,
  `option_c` varchar(255) NOT NULL,
  `option_d` varchar(255) NOT NULL,
  `correct_option` enum('A','B','C','D') NOT NULL,
  `order_num` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`question_id`),
  KEY `idx_questions_exam` (`exam_id`),
  CONSTRAINT `questions_ibfk_1` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`exam_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=97 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `questions`
--

LOCK TABLES `questions` WRITE;
/*!40000 ALTER TABLE `questions` DISABLE KEYS */;
INSERT INTO `questions` VALUES (1,1,'What does SDLC stand for?','MULTIPLE_CHOICE','[\"Software Development Life Cycle\", \"System Design Life Cycle\", \"Software Data Life Cycle\", \"System Development Logic Cycle\"]','Software Development Life Cycle',1,'EXACT','Software Development Life Cycle','System Design Life Cycle','Software Data Life Cycle','System Development Logic Cycle','A',1),(2,1,'Which methodology uses sprints of 1-4 weeks?','MULTIPLE_CHOICE','[\"Waterfall\", \"Scrum\", \"V-Model\", \"Spiral\"]','Scrum',1,'EXACT','Waterfall','Scrum','V-Model','Spiral','B',2),(3,1,'What is the first phase of the Waterfall model?','MULTIPLE_CHOICE','[\"Design\", \"Implementation\", \"Requirements Gathering\", \"Testing\"]','Requirements Gathering',1,'EXACT','Design','Implementation','Requirements Gathering','Testing','C',3),(4,1,'Which document defines what the software should do?','MULTIPLE_CHOICE','[\"User Manual\", \"Requirements Document\", \"Test Plan\", \"Source Code\"]','Requirements Document',1,'EXACT','User Manual','Requirements Document','Test Plan','Source Code','B',4),(5,1,'What is a use case diagram used for?','MULTIPLE_CHOICE','[\"Coding\", \"Database design\", \"Describing system functionality from user perspective\", \"Performance testing\"]','Describing system functionality from user perspective',1,'EXACT','Coding','Database design','Describing system functionality from user perspective','Performance testing','C',5),(6,1,'Which of these is NOT an Agile methodology?','MULTIPLE_CHOICE','[\"Scrum\", \"Kanban\", \"Waterfall\", \"XP\"]','Waterfall',1,'EXACT','Scrum','Kanban','Waterfall','XP','C',6),(7,1,'What is a sprint retrospective?','MULTIPLE_CHOICE','[\"A daily meeting\", \"A review of what went well and what to improve\", \"A product demo\", \"A coding session\"]','A review of what went well and what to improve',1,'EXACT','A daily meeting','A review of what went well and what to improve','A product demo','A coding session','B',7),(8,1,'Who is responsible for removing impediments in Scrum?','MULTIPLE_CHOICE','[\"Product Owner\", \"Scrum Master\", \"Development Team\", \"Project Manager\"]','Scrum Master',1,'EXACT','Product Owner','Scrum Master','Development Team','Project Manager','B',8),(9,1,'What is the purpose of a backlog?','MULTIPLE_CHOICE','[\"Store completed work\", \"Prioritized list of features and tasks\", \"Bug tracking\", \"Team schedule\"]','Prioritized list of features and tasks',1,'EXACT','Store completed work','Prioritized list of features and tasks','Bug tracking','Team schedule','B',9),(10,1,'Which testing is done by the end user?','MULTIPLE_CHOICE','[\"Unit Testing\", \"Integration Testing\", \"User Acceptance Testing\", \"System Testing\"]','User Acceptance Testing',1,'EXACT','Unit Testing','Integration Testing','User Acceptance Testing','System Testing','C',10),(11,4,'What is the most sequential SDLC model?','MULTIPLE_CHOICE','[\"Agile\", \"Waterfall\", \"Scrum\", \"Kanban\"]','Waterfall',1,'EXACT','Agile','Waterfall','Scrum','Kanban','B',1),(12,4,'How long is a typical Scrum sprint?','MULTIPLE_CHOICE','[\"1-4 weeks\", \"2-3 months\", \"6 months\", \"1 year\"]','1-4 weeks',1,'EXACT','1-4 weeks','2-3 months','6 months','1 year','A',2),(13,4,'What is a user story?','MULTIPLE_CHOICE','[\"A bug report\", \"A feature written from the user perspective\", \"A technical document\", \"A database schema\"]','A feature written from the user perspective',1,'EXACT','A bug report','A feature written from the user perspective','A technical document','A database schema','B',3),(14,4,'Which role prioritizes the product backlog?','MULTIPLE_CHOICE','[\"Scrum Master\", \"Developer\", \"Product Owner\", \"Tester\"]','Product Owner',1,'EXACT','Scrum Master','Developer','Product Owner','Tester','C',4),(15,4,'What is the output of the requirements phase?','MULTIPLE_CHOICE','[\"Source code\", \"Software requirements specification\", \"Test cases\", \"UML diagrams\"]','Software requirements specification',1,'EXACT','Source code','Software requirements specification','Test cases','UML diagrams','B',5),(16,3,'What does HTML stand for?','MULTIPLE_CHOICE','[\"Hyper Text Markup Language\", \"High Tech Modern Language\", \"Hyper Transfer Markup Language\", \"Home Tool Markup Language\"]','Hyper Text Markup Language',1,'EXACT','Hyper Text Markup Language','High Tech Modern Language','Hyper Transfer Markup Language','Home Tool Markup Language','A',1),(17,3,'Which CSS property changes text color?','MULTIPLE_CHOICE','[\"font-color\", \"text-color\", \"color\", \"foreground-color\"]','color',1,'EXACT','font-color','text-color','color','foreground-color','C',2),(18,3,'Which tag creates a hyperlink in HTML?','MULTIPLE_CHOICE','[\"<link>\", \"<a>\", \"<href>\", \"<url>\"]','<a>',1,'EXACT','<link>','<a>','<href>','<url>','B',3),(19,3,'What does the box model in CSS include?','MULTIPLE_CHOICE','[\"Margin, border, padding, content\", \"Width, height, depth\", \"Font, color, size\", \"Position, layout, design\"]','Margin, border, padding, content',1,'EXACT','Margin, border, padding, content','Width, height, depth','Font, color, size','Position, layout, design','A',4),(20,3,'Which JavaScript method selects an element by ID?','MULTIPLE_CHOICE','[\"getElementByClass()\", \"querySelector()\", \"getElementById()\", \"findElement()\"]','getElementById()',1,'EXACT','getElementByClass()','querySelector()','getElementById()','findElement()','C',5),(31,6,'what im i gonna do ? ','MULTIPLE_CHOICE','[\"go die\",\"diet\"]','diet',1,'EXACT','','','','','A',0),(32,6,'what im i gonna do ? ','MULTIPLE_CHOICE','[\"die \",\"go die\",\"die again\",\"diet\"]','go die',1,'EXACT','','','','','A',1),(33,6,'what is my full name?','IDENTIFICATION','[]','Rodrigo Reyes',1,'EXACT','','','','','A',2),(34,6,'am i ugly?','TRUE_FALSE','[]','True',1,'EXACT','','','','','A',3),(35,6,'what is my lolos name','IDENTIFICATION','[]','wala patay na lolo mo',1,'EXACT','','','','','A',4),(36,6,'give 3 peyborit artist','MULTIPLE_CHOICE','[\"uncle dags\",\"hev abi\",\"megan stallion \"]','',1,'EXACT','','','','','A',5),(37,7,'hello lanans','MULTIPLE_CHOICE','[\"jsjanan\",\"kamaka\",\"kwnans\",\"ajajmama\"]','jsjanan',11,'EXACT','','','','','A',0),(38,7,'jsjNzkznzbzjkz','TRUE_FALSE','[]','False',12,'EXACT','','','','','A',1),(39,7,'makakanallamamMM','MULTIPLE_CHOICE','[\"make ur bloodd\",\"nKakanNkKNz\",\"mKanNzm\"]','',1,'EXACT','','','','','A',2),(40,7,'oanaownsns?','IDENTIFICATION','[]','nKakNsj ret',1,'EXACT','','','','','A',3),(41,7,'What is the time complexity of binary search?','MULTIPLE_CHOICE','[\"O(n)\",\"O(log n)\",\"O(n^2)\",\"O(1)\"]','O(n)',5,'EXACT','','','','','A',4),(42,7,'Which data structure uses FIFO?','MULTIPLE_CHOICE','[\"Stack\",\"Queue\",\"Tree\",\"Graph\"]','Stack',5,'EXACT','','','','','A',5),(43,7,'What does SQL stand for?','MULTIPLE_CHOICE','[\"Structured Query Language\",\"Simple Query Language\",\"Standard Query Language\",\"System Query Language\"]','Structured Query Language',5,'EXACT','','','','','A',6),(44,7,'What is encapsulation in OOP?','MULTIPLE_CHOICE','[\"Hiding implementation details\",\"Inheriting properties\",\"Creating objects\",\"Overloading methods\"]','Hiding implementation details',5,'EXACT','','','','','A',7),(45,7,'Which protocol is used for secure web browsing?','MULTIPLE_CHOICE','[\"FTP\",\"SMTP\",\"HTTPS\",\"SSH\"]','FTP',5,'EXACT','','','','','A',8),(46,8,'what is my name','MULTIPLE_CHOICE','[\"my name is arnel\",\"regen Velasquez \",\"pia\",\"ayun\"]','my name is arnel',1,'EXACT','','','','','A',0),(47,8,'mahal pa ba ni arnel si lizelyn ','TRUE_FALSE','[]','True',1,'EXACT','','','','','A',1),(48,8,'ilang taon sila','IDENTIFICATION','[]','1 years',1,'EXACT','','','','','A',2),(49,8,'panis','MULTIPLE_CHOICE','[\"boom\",\"boom panis\"]','',1,'EXACT','','','','','A',3),(50,9,'What is the time complexity of binary search?','MULTIPLE_CHOICE','[\"O(n)\",\"O(log n)\",\"O(n^2)\",\"O(1)\"]','O(n)',5,'EXACT','','','','','A',0),(51,9,'Which data structure uses FIFO?','MULTIPLE_CHOICE','[\"Stack\",\"Queue\",\"Tree\",\"Graph\"]','Stack',5,'EXACT','','','','','A',1),(52,9,'What does SQL stand for?','MULTIPLE_CHOICE','[\"Structured Query Language\",\"Simple Query Language\",\"Standard Query Language\",\"System Query Language\"]','Structured Query Language',5,'EXACT','','','','','A',2),(53,9,'What is encapsulation in OOP?','MULTIPLE_CHOICE','[\"Hiding implementation details\",\"Inheriting properties\",\"Creating objects\",\"Overloading methods\"]','Hiding implementation details',5,'EXACT','','','','','A',3),(54,9,'Which protocol is used for secure web browsing?','MULTIPLE_CHOICE','[\"FTP\",\"SMTP\",\"HTTPS\",\"SSH\"]','FTP',5,'EXACT','','','','','A',4),(56,11,'mahal pa ba si arnel ni liesilyn','MULTIPLE_CHOICE','[\"oo \",\"ende \",\"pwede \",\"piro dipindi \"]','oo ',1,'EXACT','','','','','A',0),(57,11,'pogi si sir john','TRUE_FALSE','[]','True',1,'EXACT','','','','','A',1),(58,11,'sino ang bading','IDENTIFICATION','[]','justin',1,'EXACT','','','','','A',2),(59,11,'san kayo pupunta ','ENUMERATION','[\"sa skol \",\"sa ano sa anek\",\"sa dito \",\"sa dun\"]','',1,'EXACT','','','','','A',3),(60,11,'mapagmahal ba si sir john','TRUE_FALSE','[]','True',1,'EXACT','','','','','A',4),(61,12,'What is the time complexity of binary search?','MULTIPLE_CHOICE','[\"O(n)\",\"O(log n)\",\"O(n^2)\",\"O(1)\"]','O(n)',5,'EXACT','','','','','A',0),(62,12,'Which data structure uses FIFO?','MULTIPLE_CHOICE','[\"Stack\",\"Queue\",\"Tree\",\"Graph\"]','Stack',5,'EXACT','','','','','A',1),(63,12,'What does SQL stand for?','MULTIPLE_CHOICE','[\"Structured Query Language\",\"Simple Query Language\",\"Standard Query Language\",\"System Query Language\"]','Structured Query Language',5,'EXACT','','','','','A',2),(64,12,'What is encapsulation in OOP?','MULTIPLE_CHOICE','[\"Hiding implementation details\",\"Inheriting properties\",\"Creating objects\",\"Overloading methods\"]','Hiding implementation details',5,'EXACT','','','','','A',3),(65,12,'Which protocol is used for secure web browsing?','MULTIPLE_CHOICE','[\"FTP\",\"SMTP\",\"HTTPS\",\"SSH\"]','FTP',5,'EXACT','','','','','A',4),(66,13,'What is the time complexity of binary search?','MULTIPLE_CHOICE','[\"O(n)\",\"O(log n)\",\"O(n^2)\",\"O(1)\"]','O(n)',5,'EXACT','','','','','A',0),(67,13,'Which data structure uses FIFO?','MULTIPLE_CHOICE','[\"Stack\",\"Queue\",\"Tree\",\"Graph\"]','Stack',5,'EXACT','','','','','A',1),(68,13,'What does SQL stand for?','MULTIPLE_CHOICE','[\"Structured Query Language\",\"Simple Query Language\",\"Standard Query Language\",\"System Query Language\"]','Structured Query Language',5,'EXACT','','','','','A',2),(69,13,'What is encapsulation in OOP?','MULTIPLE_CHOICE','[\"Hiding implementation details\",\"Inheriting properties\",\"Creating objects\",\"Overloading methods\"]','Hiding implementation details',5,'EXACT','','','','','A',3),(70,13,'Which protocol is used for secure web browsing?','MULTIPLE_CHOICE','[\"FTP\",\"SMTP\",\"HTTPS\",\"SSH\"]','FTP',5,'EXACT','','','','','A',4),(71,14,'What is the time complexity of binary search?','MULTIPLE_CHOICE','[\"O(n)\",\"O(log n)\",\"O(n^2)\",\"O(1)\"]','O(n)',5,'EXACT','','','','','A',0),(72,14,'Which data structure uses FIFO?','MULTIPLE_CHOICE','[\"Stack\",\"Queue\",\"Tree\",\"Graph\"]','Stack',5,'EXACT','','','','','A',1),(73,14,'What does SQL stand for?','MULTIPLE_CHOICE','[\"Structured Query Language\",\"Simple Query Language\",\"Standard Query Language\",\"System Query Language\"]','Structured Query Language',5,'EXACT','','','','','A',2),(74,14,'What is encapsulation in OOP?','MULTIPLE_CHOICE','[\"Hiding implementation details\",\"Inheriting properties\",\"Creating objects\",\"Overloading methods\"]','Hiding implementation details',5,'EXACT','','','','','A',3),(75,14,'Which protocol is used for secure web browsing?','MULTIPLE_CHOICE','[\"FTP\",\"SMTP\",\"HTTPS\",\"SSH\"]','FTP',5,'EXACT','','','','','A',4),(76,15,'What is the time complexity of binary search?','MULTIPLE_CHOICE','[\"O(n)\",\"O(log n)\",\"O(n^2)\",\"O(1)\"]','O(n)',5,'EXACT','','','','','A',0),(77,15,'Which data structure uses FIFO?','MULTIPLE_CHOICE','[\"Stack\",\"Queue\",\"Tree\",\"Graph\"]','Stack',5,'EXACT','','','','','A',1),(78,15,'What does SQL stand for?','MULTIPLE_CHOICE','[\"Structured Query Language\",\"Simple Query Language\",\"Standard Query Language\",\"System Query Language\"]','Structured Query Language',5,'EXACT','','','','','A',2),(79,15,'What is encapsulation in OOP?','MULTIPLE_CHOICE','[\"Hiding implementation details\",\"Inheriting properties\",\"Creating objects\",\"Overloading methods\"]','Hiding implementation details',5,'EXACT','','','','','A',3),(80,15,'Which protocol is used for secure web browsing?','MULTIPLE_CHOICE','[\"FTP\",\"SMTP\",\"HTTPS\",\"SSH\"]','FTP',5,'EXACT','','','','','A',4),(81,16,'what is the periodic symbol of gold','MULTIPLE_CHOICE','[\"Au\",\"Ag\",\"Go\",\"Al\"]','Au',2,'EXACT','','','','','A',0),(82,16,'what is the periodic symbol of gold','MULTIPLE_CHOICE','[\"Au\",\"Ag\",\"Go\",\"Al\"]','Au',2,'EXACT','','','','','A',1),(83,16,'what is the periodic symbol of gold','MULTIPLE_CHOICE','[\"Au\",\"Ag\",\"Go\",\"Al\"]','Au',2,'EXACT','','','','','A',2),(84,16,'lalake ba si justin','TRUE_FALSE','[]','False',2,'EXACT','','','','','A',3),(85,16,'babae ba si sofia','TRUE_FALSE','[]','True',2,'EXACT','','','','','A',4),(87,18,'What is the time complexity of binary search?','MULTIPLE_CHOICE','[\"O(n)\",\"O(log n)\",\"O(n^2)\",\"O(1)\"]','O(n)',2,'EXACT','','','','','A',0),(88,18,'Which data structure uses FIFO?','MULTIPLE_CHOICE','[\"Stack\",\"Queue\",\"Tree\",\"Graph\"]','Stack',2,'EXACT','','','','','A',1),(89,18,'What does SQL stand for?','MULTIPLE_CHOICE','[\"Structured Query Language\",\"Simple Query Language\",\"Standard Query Language\",\"System Query Language\"]','Structured Query Language',2,'EXACT','','','','','A',2),(90,18,'What is encapsulation in OOP?','MULTIPLE_CHOICE','[\"Hiding implementation details\",\"Inheriting properties\",\"Creating objects\",\"Overloading methods\"]','Hiding implementation details',2,'EXACT','','','','','A',3),(91,18,'Which protocol is used for secure web browsing?','MULTIPLE_CHOICE','[\"FTP\",\"SMTP\",\"HTTPS\",\"SSH\"]','FTP',2,'EXACT','','','','','A',4),(92,19,'What is the time complexity of binary search?','MULTIPLE_CHOICE','[\"O(n)\",\"O(log n)\",\"O(n^2)\",\"O(1)\"]','O(n)',5,'EXACT','','','','','A',0),(93,19,'Which data structure uses FIFO?','MULTIPLE_CHOICE','[\"Stack\",\"Queue\",\"Tree\",\"Graph\"]','Stack',5,'EXACT','','','','','A',1),(94,19,'What does SQL stand for?','MULTIPLE_CHOICE','[\"Structured Query Language\",\"Simple Query Language\",\"Standard Query Language\",\"System Query Language\"]','Structured Query Language',5,'EXACT','','','','','A',2),(95,19,'What is encapsulation in OOP?','MULTIPLE_CHOICE','[\"Hiding implementation details\",\"Inheriting properties\",\"Creating objects\",\"Overloading methods\"]','Hiding implementation details',5,'EXACT','','','','','A',3),(96,19,'Which protocol is used for secure web browsing?','MULTIPLE_CHOICE','[\"FTP\",\"SMTP\",\"HTTPS\",\"SSH\"]','FTP',5,'EXACT','','','','','A',4);
/*!40000 ALTER TABLE `questions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `roles` (
  `role_id` int(11) NOT NULL AUTO_INCREMENT,
  `role_name` varchar(20) NOT NULL,
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `role_name` (`role_name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `roles`
--

LOCK TABLES `roles` WRITE;
/*!40000 ALTER TABLE `roles` DISABLE KEYS */;
INSERT INTO `roles` VALUES (1,'STUDENT'),(2,'TEACHER');
/*!40000 ALTER TABLE `roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sessions`
--

DROP TABLE IF EXISTS `sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sessions` (
  `session_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `token` varchar(64) NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`session_id`),
  UNIQUE KEY `token` (`token`),
  KEY `user_id` (`user_id`),
  KEY `idx_sessions_token` (`token`),
  CONSTRAINT `sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=157 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sessions`
--

LOCK TABLES `sessions` WRITE;
/*!40000 ALTER TABLE `sessions` DISABLE KEYS */;
INSERT INTO `sessions` VALUES (53,2,'e1c1cdc566e46e3aa126d7df15efe30033fc9e90c47db09101660df3ea9fccf3','2026-08-07 17:32:24','2026-07-31 15:32:24'),(102,4,'0ee739382a29d53eb5df74325e26de6d9251b32c0474204542fb90ee11b9aef6','2026-08-08 08:29:33','2026-08-01 00:29:33'),(103,1,'8c82680c91c6b520b407c5df85ef5b4ef3d8bd50e4c13caa90989e9c0976afaf','2026-08-08 08:30:01','2026-08-01 00:30:01'),(104,4,'d1fbe45bbf33990ac23bbe7c6413038f5c7cf212813546dc8f04437638e911fd','2026-08-08 08:35:10','2026-08-01 00:35:10'),(105,1,'616d806e5ff8798c34ed5a3fa1e798cf0edbdf5b085a0ed006b6e569e9d16c14','2026-08-08 08:41:30','2026-08-01 00:41:30'),(108,4,'ab987d3856c0c52a9faad1c27143bed6aaa0492e1491ad4755f2d3a308543680','2026-08-08 08:45:24','2026-08-01 00:45:24'),(109,4,'853fe5859d7db6a02667ffa001a445c3f29a8b7bb0dd112fde519e49968d363b','2026-08-08 08:45:34','2026-08-01 00:45:34'),(110,1,'58a4136e083919cce32ede6198dd70b3e761bb09a1c8c6536e88b4b963c5bb11','2026-08-08 08:46:55','2026-08-01 00:46:55'),(111,4,'a245d390fc2826895507d6758b4dff4671f13a0cf4c4470acf13b84c170f82f2','2026-08-08 08:49:36','2026-08-01 00:49:36'),(113,1,'613aad7d2230fcfc3e231fbf01266a91eac983391745e9021213a053998236fb','2026-08-08 08:56:38','2026-08-01 00:56:38'),(114,4,'618ba657cdf66738ea0a254dbccfe4bb518b136a01c4ab6ef9dd566b85bcfb26','2026-08-08 08:57:51','2026-08-01 00:57:51'),(115,4,'089172d18e3c76b733fcdfea8f2023d8fa7817fe60764a4d91b51d694237de95','2026-08-08 08:58:19','2026-08-01 00:58:19'),(116,1,'b5d860283fba5f247117271e0918ec02bfc12b8d85e26f05841066c4156820cc','2026-08-08 08:58:35','2026-08-01 00:58:35'),(117,4,'fe1a1d5d7ecd506371cc1f6f8bde1f070561bf422ee4a690f01f56660e66a86c','2026-08-08 09:00:43','2026-08-01 01:00:43'),(118,1,'fb9c5234010d6e53151ce00b97e5d5644249f5b289301db53c5723a31f9df706','2026-08-08 09:03:09','2026-08-01 01:03:09'),(119,4,'b33f9436369b4f0c81f62405b30ed46b8dc18f4a14922d639d90cbfe4fd81081','2026-08-08 09:07:05','2026-08-01 01:07:05'),(120,1,'11bdb7cb2bd585bbd5cebe3881fd5993ead06b96213d7d818e77047ee234a1f6','2026-08-08 09:08:31','2026-08-01 01:08:31'),(122,4,'996e42081aaa5d24bded87c4385a68c4c67cc09e98f29ddac2fb9cc0200df15c','2026-08-08 09:59:41','2026-08-01 01:59:41'),(123,1,'04a677b000764071554135ca44caa8247d8c592c7cd713dcbe7eb1d83905c933','2026-08-08 10:00:32','2026-08-01 02:00:32'),(124,4,'88d94e8dacc15e45560857a2e2add915125130516f1816bdbe8efe6d0e2636a6','2026-08-08 10:04:42','2026-08-01 02:04:42'),(125,1,'d47f541a532c6322b2546a952630af9ac3031da9c3d8558de9ed1f72357b8e1c','2026-08-20 15:35:21','2026-08-13 07:35:21'),(126,4,'46e2fb4fef88b35bd7a1f12362b5493af048763e5b8430151b0cf3ff6f660a02','2026-08-22 09:24:22','2026-08-15 01:24:22'),(127,1,'c377ac0ee15c96c802c007558d4319e93ce92e63ee5ef8a850b60e4adce08a56','2026-08-22 09:37:08','2026-08-15 01:37:08'),(128,5,'4c5e341daabadad9fd3c264dcba24b2a1baa29f343a5abe581e0b5ea6b891fc4','2026-08-22 09:40:07','2026-08-15 01:40:07'),(129,4,'822297e27f5f0b062d01db14202964d06a2c6278d12875c842d9c50db35a4a00','2026-08-22 09:40:44','2026-08-15 01:40:44'),(130,6,'166a0b840687788aaeb65d31a4aee63de943193d1ccc05b058a63f343769c285','2026-08-22 09:41:26','2026-08-15 01:41:26'),(131,6,'774e84f5ed8cbbb8a7a4aff650a83c547d301f38d1caf1151b6017b1808a365b','2026-08-22 09:41:42','2026-08-15 01:41:42'),(132,6,'1ee3844986dfd74ef0a2e560514581c2d634c793d773353f072999765719fca7','2026-08-22 09:42:14','2026-08-15 01:42:14'),(133,6,'7ccaf6b122dddd3c92f77107c6c0b570315ab63b81704830ac2168d52ba5fee9','2026-08-22 09:42:24','2026-08-15 01:42:24'),(134,4,'371eb315308876ecb8fa90244f57c7d1b5bb93bd895aec0f395a247ac157ce5b','2026-08-22 10:03:30','2026-08-15 02:03:30'),(135,4,'11edc4c90b07da02d1cf0d8351c5ee8c596748ef5627a0e84be8582a04940672','2026-08-22 10:03:44','2026-08-15 02:03:44'),(136,4,'845e1d0543340ab2f8f346a9acefad1fa0837c1a86f4657d656dcd8440e4adc8','2026-08-22 10:03:44','2026-08-15 02:03:44'),(137,1,'f5cfc815383fbce1505057554cb24f134bbf912af81c69fbbeddcaa9a2d1cde7','2026-08-22 10:04:25','2026-08-15 02:04:25'),(138,4,'d7e71b84de4f4010071b60735e6b28f07c4029179fb08a1874868a5e46a7a64f','2026-08-22 10:04:48','2026-08-15 02:04:48'),(139,4,'a44082f3030c5366578775ac854ad43000bdd7c1e20b1ae61650a3de4673b9a5','2026-08-22 10:04:56','2026-08-15 02:04:56'),(140,1,'1ee89140f898aee35cceec4cfd0e5cc8b253f6a82af209bd2beb5b5e3ee64d91','2026-08-22 10:06:49','2026-08-15 02:06:49'),(141,1,'9be3d21583a5c11a391708aa771e7c6dc00a172f49e7948d374565a182308238','2026-08-22 10:07:57','2026-08-15 02:07:57'),(142,1,'85d60966588f81221c2a225e559b40a3ca10e0d35bccaa410b0adce135ef2db9','2026-08-22 10:08:07','2026-08-15 02:08:07'),(143,1,'7ceea7cff75ed63aacede19d78e74e7617cece0f3a15d98449decbf258207a99','2026-08-22 10:09:42','2026-08-15 02:09:42'),(144,1,'e0f1b92616e69f92246b12177647ca506c42dce81dba2532e267292c1c7163aa','2026-08-22 10:09:54','2026-08-15 02:09:54'),(145,1,'3ccedc826d26f347cd907fcbb53d952b6e8cfadbe9b6b093f7cc835a9b84e0e5','2026-08-22 10:10:06','2026-08-15 02:10:06'),(146,1,'ec8c0dc166d9cf573571c97e125deb8651558d69671867d9796bf7e47aff6b09','2026-08-22 10:10:11','2026-08-15 02:10:11'),(147,1,'ea3feae0720e392e2d13879e3f8c02daf1d26a4ff79928567e2f93fe367aaad9','2026-08-22 10:12:09','2026-08-15 02:12:09'),(148,1,'dc1adba6b07f193be14f0d31a149f8c5081293938686fd77404346d4616c6be3','2026-08-22 10:14:29','2026-08-15 02:14:29'),(149,4,'c0889f0ce0e77ae6dfb0b1b014d3329c0e312b0b39700d58e630afac1809afdc','2026-08-22 10:24:27','2026-08-15 02:24:27'),(150,1,'1a12379fb9b6db4fd819deb04471c82eb7c31026c0aae1213613253cad0889ee','2026-08-22 10:25:10','2026-08-15 02:25:10'),(151,4,'d9174d3d01b7709986b977ec4a5b4d1c6b2a9bfed2dadf0371224b13965b36a0','2026-08-22 10:30:33','2026-08-15 02:30:33'),(152,1,'d6f27879416e54be2522d07a54e4c88831554983fb0961747f27162efaa1c359','2026-08-22 10:33:26','2026-08-15 02:33:26'),(153,4,'c7e0ac82ea2cfa306493bea92d41a56bdb53cc4c100dd9b0d734065a09a3ee3e','2026-08-22 10:35:06','2026-08-15 02:35:06'),(154,1,'1c09c464f48c06d43f8fe3e73e7e20555d722743fda1882ca28ebc167741e9df','2026-08-22 10:35:22','2026-08-15 02:35:22'),(155,4,'5a9ed75d15961b221b7f306f44470b39395c156022432928c8a2e492a919962d','2026-08-22 10:36:10','2026-08-15 02:36:10'),(156,1,'3b0241afdedff09afc5d8a7494ab5632ba67d0aad5d8a35e2cb49bd961c66c58','2026-08-22 10:37:48','2026-08-15 02:37:48');
/*!40000 ALTER TABLE `sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `user_id` int(11) NOT NULL AUTO_INCREMENT,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `username` varchar(100) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `student_id` varchar(30) DEFAULT NULL,
  `year_level` varchar(20) DEFAULT NULL,
  `section` varchar(50) DEFAULT NULL,
  `status` enum('ACTIVE','INACTIVE','BANNED') DEFAULT 'ACTIVE',
  `role_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`role_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Ricardo','Domingo','prof.domingo','domingo@rmc.edu.ph','$2y$10$qCDKEOWi8KtwlNVRMStO7OIvFmDbsrPbLUN2aAZ3qUkVBTfnE8MNm',NULL,NULL,NULL,'ACTIVE',2,'2026-07-26 17:40:34'),(2,'Maria','Santos','prof.santos','santos@rmc.edu.ph','$2y$10$qCDKEOWi8KtwlNVRMStO7OIvFmDbsrPbLUN2aAZ3qUkVBTfnE8MNm',NULL,NULL,NULL,'ACTIVE',2,'2026-07-26 17:40:34'),(3,'Juan','Reyes','prof.reyes','reyes@rmc.edu.ph','$2y$10$qCDKEOWi8KtwlNVRMStO7OIvFmDbsrPbLUN2aAZ3qUkVBTfnE8MNm',NULL,NULL,NULL,'ACTIVE',2,'2026-07-26 17:40:34'),(4,'Sofia','Cruz','sofia.cruz','sofia.cruz@rmc.edu.ph','$2y$10$qCDKEOWi8KtwlNVRMStO7OIvFmDbsrPbLUN2aAZ3qUkVBTfnE8MNm','136578100123','3rd Year','BSIT 3-A','ACTIVE',1,'2026-07-26 17:40:34'),(5,'Miguel','Reyes','miguel.reyes','miguel.reyes@rmc.edu.ph','$2y$10$qCDKEOWi8KtwlNVRMStO7OIvFmDbsrPbLUN2aAZ3qUkVBTfnE8MNm','136578100124','3rd Year','BSIT 3-A','ACTIVE',1,'2026-07-26 17:40:34'),(6,'Ana','Garcia','ana.garcia','ana.garcia@rmc.edu.ph','$2y$10$qCDKEOWi8KtwlNVRMStO7OIvFmDbsrPbLUN2aAZ3qUkVBTfnE8MNm','136578100125','2nd Year','BSIT 2-B','ACTIVE',1,'2026-07-26 17:40:34');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-16 13:33:49
