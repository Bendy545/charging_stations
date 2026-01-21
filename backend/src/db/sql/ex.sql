-- MySQL dump 10.13  Distrib 8.0.42, for macos15 (x86_64)
--
-- Host: 127.0.0.1    Database: charging_station_db
-- ------------------------------------------------------
-- Server version	9.3.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `charging_sessions`
--

DROP TABLE IF EXISTS `charging_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `charging_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `station_id` int NOT NULL,
  `charger_name` varchar(100) NOT NULL,
  `start_date` datetime NOT NULL,
  `end_date` datetime DEFAULT NULL,
  `total_kwh` decimal(10,3) NOT NULL,
  `start_card` varchar(50) DEFAULT NULL,
  `end_interval_15min` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_end_interval` (`end_interval_15min`),
  KEY `idx_station_interval` (`station_id`,`end_interval_15min`),
  CONSTRAINT `charging_sessions_ibfk_1` FOREIGN KEY (`station_id`) REFERENCES `stations` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2799 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `distributed_sessions`
--

DROP TABLE IF EXISTS `distributed_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `distributed_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` int NOT NULL,
  `station_id` int NOT NULL,
  `interval_15min` datetime NOT NULL,
  `energy_kwh` decimal(10,3) NOT NULL,
  `proportion` decimal(5,4) NOT NULL,
  `overlap_minutes` decimal(6,2) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_session_interval` (`session_id`,`interval_15min`),
  KEY `idx_interval` (`interval_15min`),
  KEY `idx_station_interval` (`station_id`,`interval_15min`),
  CONSTRAINT `distributed_sessions_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `charging_sessions` (`id`),
  CONSTRAINT `distributed_sessions_ibfk_2` FOREIGN KEY (`station_id`) REFERENCES `stations` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=27721 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `loss_analysis`
--

DROP TABLE IF EXISTS `loss_analysis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `loss_analysis` (
  `id` int NOT NULL AUTO_INCREMENT,
  `station_id` int NOT NULL,
  `period_start` date NOT NULL,
  `period_end` date NOT NULL,
  `total_consumption_kwh` decimal(12,3) NOT NULL,
  `total_delivered_kwh` decimal(12,3) NOT NULL,
  `total_reactive_kwh` decimal(12,3) DEFAULT '0.000',
  `loss_kwh` decimal(12,3) NOT NULL,
  `loss_percentage` decimal(10,2) DEFAULT NULL,
  `calculated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_station_period` (`station_id`,`period_start`,`period_end`),
  KEY `idx_period` (`period_start`,`period_end`),
  CONSTRAINT `loss_analysis_ibfk_1` FOREIGN KEY (`station_id`) REFERENCES `stations` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5022 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `power_consumption`
--

DROP TABLE IF EXISTS `power_consumption`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `power_consumption` (
  `id` int NOT NULL AUTO_INCREMENT,
  `timestamp` datetime NOT NULL,
  `station_id` int NOT NULL,
  `active_power_kwh` decimal(10,3) NOT NULL,
  `reactive_power_kwh` decimal(10,3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_timestamp_station` (`timestamp`,`station_id`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_station_time` (`station_id`,`timestamp`),
  CONSTRAINT `power_consumption_ibfk_1` FOREIGN KEY (`station_id`) REFERENCES `stations` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=205756 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `prediction_cache`
--

DROP TABLE IF EXISTS `prediction_cache`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `prediction_cache` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `station_id` int NOT NULL,
  `prediction_date` date NOT NULL,
  `predicted_loss_kwh` decimal(10,4) DEFAULT NULL,
  `predicted_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `id` (`id`),
  UNIQUE KEY `station_id` (`station_id`,`prediction_date`)
) ENGINE=InnoDB AUTO_INCREMENT=436 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `stations`
--

DROP TABLE IF EXISTS `stations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `station_code` varchar(50) NOT NULL,
  `station_name` varchar(100) NOT NULL,
  `location` varchar(100) DEFAULT 'Jeníšov',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `station_code` (`station_code`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-20 20:54:25
