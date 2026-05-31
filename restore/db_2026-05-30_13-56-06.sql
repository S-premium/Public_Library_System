-- MariaDB dump 10.19  Distrib 10.4.32-MariaDB, for Win64 (AMD64)
--
-- Host: 127.0.0.1    Database: s-premium
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
-- Table structure for table `account_requests`
--

DROP TABLE IF EXISTS `account_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `account_requests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `username` varchar(255) NOT NULL,
  `request_type` enum('deactivate','delete','renew','register') NOT NULL,
  `reason` text NOT NULL,
  `status` enum('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  `reviewed_by` int(11) DEFAULT NULL,
  `reviewed_at` datetime DEFAULT NULL,
  `admin_note` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `card_id` int(11) DEFAULT NULL COMMENT 'library_cards.id',
  `renewal1_checked` tinyint(1) DEFAULT NULL,
  `renewal1_date` date DEFAULT NULL,
  `renewal2_checked` tinyint(1) DEFAULT NULL,
  `renewal2_date` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `reviewed_by` (`reviewed_by`),
  KEY `idx_ar_card` (`card_id`),
  CONSTRAINT `account_requests_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `account_requests_ibfk_2` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=79 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `account_requests`
--

LOCK TABLES `account_requests` WRITE;
/*!40000 ALTER TABLE `account_requests` DISABLE KEYS */;
INSERT INTO `account_requests` VALUES (71,70,'faf7cfd842a3465e5f5e4e30c2174d29978c5fad3b16300fdcd5745f0320fafd','register','New user registration awaiting admin approval.','approved',1,'2026-05-04 11:08:48','','2026-05-04 11:07:30',NULL,NULL,NULL,NULL,NULL),(75,73,'128d8758524723c62e95cd4d547ad26b409077f48d51540726c340608217000d','register','New user registration awaiting admin approval.','approved',1,'2026-05-10 13:27:13','','2026-05-10 13:26:57',NULL,NULL,NULL,NULL,NULL),(77,75,'fc2f85a9d1e8c4b14e4f0ab402e59967d37ae8cbae9534ab0bbfac843a427da7','register','New user registration awaiting admin approval.','approved',1,'2026-05-14 13:26:06','','2026-05-14 13:25:02',NULL,NULL,NULL,NULL,NULL),(78,75,'fc2f85a9d1e8c4b14e4f0ab402e59967d37ae8cbae9534ab0bbfac843a427da7','renew','No reason provided','approved',1,'2026-05-14 13:33:36','okay na','2026-05-14 13:33:22',21,1,'2026-05-14',0,NULL);
/*!40000 ALTER TABLE `account_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `announcements`
--

DROP TABLE IF EXISTS `announcements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `announcements` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(120) NOT NULL,
  `body` text NOT NULL,
  `category` enum('general','urgent','event','reminder') DEFAULT 'general',
  `pinned` tinyint(1) DEFAULT 0,
  `author` varchar(100) DEFAULT 'Librarian',
  `target_user_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT NULL ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_ann_target_user` (`target_user_id`),
  CONSTRAINT `fk_ann_target_user` FOREIGN KEY (`target_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `announcements`
--

LOCK TABLES `announcements` WRITE;
/*!40000 ALTER TABLE `announcements` DISABLE KEYS */;
INSERT INTO `announcements` VALUES (2,'New Arrivals in Fiction Section','We are excited to announce that the latest bestsellers and popular fiction titles have arrived! Visit the fiction section to explore new books and reserve your favorites today.','general',0,'Keiru Tuerto (Librarian)',NULL,'2026-03-03 19:17:34',NULL),(3,'Temporary Closure for Maintenance','The library will be closed tomorrow, March 4, 2026, from 8:00 AM to 5:00 PM for scheduled maintenance. We apologize for any inconvenience and encourage you to plan your visits accordingly.','urgent',1,'Keiru Tuerto (Librarian)',NULL,'2026-03-03 19:17:52','2026-03-03 19:32:57'),(4,'Return Overdue Books','Friendly reminder to return any overdue books by the end of this week to avoid late fees. Check your account online to see your borrowed items and due dates.','general',0,'Keiru Tuerto (Librarian)',NULL,'2026-03-03 19:18:18',NULL),(5,'Library Announcement','Please be informed that the library system is now updated. Students are encouraged to return borrowed books on or before the due date to avoid penalties.\n\nIf you wish to borrow new books, you may visit the library or use the library system to check the available inventory.\n\nThank you and have a great day!','general',1,'Anthony Ojera (Admin)',NULL,'2026-03-11 16:34:24','2026-03-11 18:44:22'),(6,'Library System Update','Good day, everyone!\n\nWe would like to inform all users that the library system has been recently updated to improve performance and security. Please report any issues you encounter while using the system to the library staff.\n\nThank you for your cooperation.','general',0,'Anthony Ojera (Admin)',NULL,'2026-03-11 18:44:00',NULL),(70,'Registration Approved — Welcome! ????','Your registration has been approved by the Admin. You can now log in.','general',0,'Anthony Ojera (Admin)',73,'2026-05-10 13:27:18',NULL),(77,'Library Card Renewal — Approved ✓','Your library card renewal has been approved.','general',0,'Anthony Ojera (Admin)',70,'2026-05-14 11:55:31',NULL),(78,'Registration Approved — Welcome! ????','Your registration has been approved by the Admin. You can now log in.','general',0,'Anthony Ojera (Admin)',75,'2026-05-14 13:26:10',NULL),(79,'Library Card Renewal — Approved ✓','Your library card renewal has been approved. Note: \"okay na\"','general',0,'Anthony Ojera (Admin)',75,'2026-05-14 13:33:36',NULL),(80,'hello world','hello my boy','general',0,'Krystal Sangacena (Librarian)',70,'2026-05-20 14:26:05',NULL);
/*!40000 ALTER TABLE `announcements` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `backup_logs`
--

DROP TABLE IF EXISTS `backup_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `backup_logs` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `backup_type` enum('auto','manual') NOT NULL DEFAULT 'auto',
  `scope` varchar(100) NOT NULL DEFAULT 'Database + Files',
  `file_name` varchar(255) NOT NULL DEFAULT '',
  `file_size_bytes` bigint(20) NOT NULL DEFAULT 0,
  `dropbox_path` varchar(500) NOT NULL DEFAULT '',
  `status` enum('success','failed') NOT NULL DEFAULT 'success',
  `error_message` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `backup_logs`
--

LOCK TABLES `backup_logs` WRITE;
/*!40000 ALTER TABLE `backup_logs` DISABLE KEYS */;
/*!40000 ALTER TABLE `backup_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `book_inventory`
--

DROP TABLE IF EXISTS `book_inventory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `book_inventory` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `book_id` int(11) NOT NULL,
  `volumes` int(11) NOT NULL DEFAULT 1,
  `available_copies` int(11) NOT NULL DEFAULT 1,
  `damaged_copies` int(11) NOT NULL DEFAULT 0,
  `lost_copies` int(11) NOT NULL DEFAULT 0,
  `shelf_location` varchar(255) DEFAULT NULL,
  `status` varchar(50) NOT NULL DEFAULT 'Available',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `book_id` (`book_id`),
  CONSTRAINT `book_inventory_ibfk_1` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `book_inventory`
--

LOCK TABLES `book_inventory` WRITE;
/*!40000 ALTER TABLE `book_inventory` DISABLE KEYS */;
INSERT INTO `book_inventory` VALUES (2,52,100,100,0,0,'section b - row 15','Available','2026-03-03 14:14:51'),(11,59,100,100,0,0,'A-Row2','Available','2026-03-05 11:28:16'),(18,66,150,145,0,0,NULL,'Available','2026-03-25 07:45:31'),(19,67,1,1,0,0,'A-Row 2','Available','2026-04-29 03:34:24'),(21,69,50,38,10,2,'A-Row 2','Available','2026-04-29 06:07:50'),(22,70,100,80,10,5,'A-Row 2','Available','2026-04-29 09:07:31'),(24,72,50,43,5,2,'A-Row 2','Available','2026-05-18 05:57:35');
/*!40000 ALTER TABLE `book_inventory` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `book_return_items`
--

DROP TABLE IF EXISTS `book_return_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `book_return_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `return_id` int(11) NOT NULL,
  `card_book_id` int(11) DEFAULT NULL,
  `book_title` varchar(500) DEFAULT NULL,
  `book_author` varchar(300) DEFAULT NULL,
  `book_isbn` varchar(100) DEFAULT NULL,
  `qty_returned` int(11) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `return_id` (`return_id`),
  CONSTRAINT `book_return_items_ibfk_1` FOREIGN KEY (`return_id`) REFERENCES `book_returns` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `book_return_items`
--

LOCK TABLES `book_return_items` WRITE;
/*!40000 ALTER TABLE `book_return_items` DISABLE KEYS */;
INSERT INTO `book_return_items` VALUES (29,18,47,'SLEEPARALIS','F. Scott Fitzgerald','978-3-16-148410-0',1),(30,18,48,'The Pilgrimage','Paulo Coelho','9780061687457',1);
/*!40000 ALTER TABLE `book_return_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `book_returns`
--

DROP TABLE IF EXISTS `book_returns`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `book_returns` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `card_id` int(11) NOT NULL,
  `return_date` date NOT NULL,
  `processed_by` int(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `card_id` (`card_id`),
  KEY `processed_by` (`processed_by`),
  CONSTRAINT `book_returns_ibfk_1` FOREIGN KEY (`card_id`) REFERENCES `library_cards` (`id`) ON DELETE CASCADE,
  CONSTRAINT `book_returns_ibfk_2` FOREIGN KEY (`processed_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `book_returns`
--

LOCK TABLES `book_returns` WRITE;
/*!40000 ALTER TABLE `book_returns` DISABLE KEYS */;
INSERT INTO `book_returns` VALUES (18,21,'2026-05-14',1,'2026-05-14 13:41:19');
/*!40000 ALTER TABLE `book_returns` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `books`
--

DROP TABLE IF EXISTS `books`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `books` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `call_number` varchar(255) DEFAULT NULL,
  `date_received` date DEFAULT NULL,
  `class` varchar(500) DEFAULT NULL,
  `author` varchar(1000) DEFAULT NULL,
  `author_index` varchar(64) DEFAULT NULL,
  `title` varchar(1000) DEFAULT NULL,
  `title_index` varchar(64) DEFAULT NULL,
  `isbn` varchar(1000) DEFAULT NULL,
  `isbn_index` varchar(64) DEFAULT NULL,
  `edition` varchar(100) DEFAULT NULL,
  `page_count` smallint(5) unsigned DEFAULT NULL,
  `category` varchar(500) DEFAULT NULL,
  `source_of_fund` varchar(255) DEFAULT NULL,
  `cost_price` decimal(10,2) DEFAULT NULL,
  `publisher` varchar(1000) DEFAULT NULL,
  `copy_right` varchar(255) DEFAULT NULL,
  `subtitle` varchar(500) DEFAULT NULL,
  `published_date` varchar(20) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `language` char(5) DEFAULT 'en',
  `thumbnail_url` varchar(800) DEFAULT NULL,
  `api_source` varchar(50) DEFAULT NULL,
  `is_borrowable` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `isbn` (`isbn`) USING HASH,
  KEY `idx_title_index` (`title_index`),
  KEY `idx_author_index` (`author_index`),
  KEY `idx_isbn_index` (`isbn_index`)
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `books`
--

LOCK TABLES `books` WRITE;
/*!40000 ALTER TABLE `books` DISABLE KEYS */;
INSERT INTO `books` VALUES (52,NULL,NULL,'gAAAAABp8ZTqlfa2HBkVAP-3alZlAFVRTki9nWVlZkylrBzjxfL0yqghEmVd5cWi01JPNHjRA5ADFIUMmVc67tTKtRSwR2DFcw==','gAAAAABp8ZTqH_wkWKOYviWewjxVqNwZFaG5t47eTaOWF6RHAz3YJuCHxWNdhNuEDeN8jo2YEv03yFXSj8IGiOg9ROSwer9XgQ==','5c2b134fa724ec36c49c1622e5e3059b4bf11867c699d3a7d2bcdf30087108c8','gAAAAABp8ZTqt-OPzav9meH4-93SsUnkBtyY9hz4OIrb1kU-YJ577Q6dEz6KTCsc5fcXxO_mBfyQZIAB26ARhSAQmuPajCdvuA==','a61858a4ee013d21cdbb563f08086c3475fa7e4b667a7e7ff048d8ab9ecdab73','gAAAAABp8ZTqv1mazmLMAdiVF9as6Fb-ys-kb2KDMdsCegIt3_UC8WbKuLECwJKDgq9Rw_-o17YikKpFtlL7_MBCQsUSKprdJTF34aDgnOb3WiF8SiObFrg=','97a3dd68e682966f271e916a4c4f0ecb1a62fda4b737bbd2e4f86664607913a7',NULL,NULL,'gAAAAABp8ZTqYuqn7NWUDLVrsmEfXLXVfOL265FGdK9mR0blgfte9rgOJUSfdl8FLvwAY7k8_BjuBsK__9wr15GGwxscDXhK_Q==',NULL,NULL,'gAAAAABp8ZTqRs4NmGLErFvEerT6V29x10sSENxdqL8FX2nLXvlADQQWB-atozt7l2-CyIElS-imYRz8tRb9K2uKdKAeQy9qjg==',NULL,NULL,NULL,NULL,'en',NULL,NULL,1,'2026-03-03 14:14:51','2026-05-12 06:10:00'),(59,NULL,NULL,'gAAAAABpqWjQ7kqlUkGHdUbNxb-plRnkqm3Y0sKw0KoEq9DDzojUHjF2uqv1K65WMPLNbslupFTOB4LbMj-sNfmsr-gX5-TxsA==','gAAAAABpqWjQz090faTCv6RS_ytn30hu5MSYAoAj8nS_OkgaWFvCqTu2DRbmItu2pbumKrU1nxRBOZpOyaaP1aCNdpsLfiz8HsPMsoTo-_rFPcgRQsmkOiU=','de360accd91fcc0d27cedf9a8b6d4145d5c6e019c6ccdff7e6cde4d833a8b575','gAAAAABpqWjQJ2N0lBfE2uxt6kzPyNEkzhGUUMgInwPpFLmoke_0OFyKpcKfy47DJrehDd96r3xOtifPKy3Fdhnt_2ENQL9Lgw==','a36dc5fb6fce329e12e5e9011d25bb59e29169962e0f4c1f35b1065c37a7c296','gAAAAABpqWjQSMddTPrZvz60wmaNaNgxyuIm6Hl-2m9VZqvCQ3W4vP38o8QfN5usn3B6PE0GahmvW4_uEc0KQ6eXDOjlzp5QRg==','42a5fa90c97072adddfeba88b915b14a37d47e1ba42aa3db73b857dd8cc29db0',NULL,388,'gAAAAABpqWjQii0GKHeOgOP0d2Mezs0NN6oe4HiLAPe1J1sJG7FQOtyItqUHmsAnamAjl3Mm1rkbsV5EGarjc718_pnvDrR5XU1iLm6W_cpMNzEbU7P7vLc=',NULL,NULL,'gAAAAABpqWjQr0iBuNNBrN3r-_JwjFhUtB7h9GW5eGzvSzS55ZaFf3b3t0QrhrAUHcwiBqiV8B8fv3q1CJV3rBVawaZjrMI3hwOZxmVuT62lSokZFgmF-eE=',NULL,'heelo world','1986','A story of love and social awareness during the American occupation.','tl','https://books.google.com/books/content?id=-aQ2vMJzYYkC&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api','Google Books',0,'2026-03-05 11:28:16','2026-05-12 06:10:00'),(66,NULL,NULL,NULL,'gAAAAABpyURsa4nAlf3144qLYREgaUNA9Z5-GFoMmlrOH8IKFlmW2l2jrPolQ8_w-JY72eGmFOPKqmBVZWoIV0bNOiW71XGV5Q==','e1d52fc04b98281363ebe6778750ee3c85b21185a109604a2af0e4dbe585da22','gAAAAABpyURs2eH5aOCUkXVtuG7j8EinKeEImAGjkIiZjuFVcPSBBxT1MC6vNdDII73TdIPHfL16T7RTFFxT2a1wlNEqCtY5Rw==','24a3dded1b4249e9e80707679455015833cc67a7c007e3d8a5974c79a367a847','gAAAAABpyURsZrmBX5vtrDwqHpdJqu3ZkRnRV5pjwNbMc5N4lVNJ7SJOG9XvngiiYiZXsvIknkelOVugxWBgt4YEfh3itf5mag==','2eb7abddb61a5dddac866561ca35432112b8dc7e884e1b21c5912d7256f256de',NULL,NULL,'gAAAAABpyURsCrXNw_MUcIWxolz1_vSVvdZqNWDFtMb_8eOnKbO9GlMiss_bUeXkwsxs5fxmfYnDvBTwHHEVD4M-U_rvoLcjmQ==',NULL,NULL,'gAAAAABpyURsodr1Tv9kYSIx3tqBi5fWW8i850WJSJxBO0EgCC3nBhdSWhM-Ety3wVAfl8LIYMacpgEkGJppm1smj7EqJ1o30A==',NULL,NULL,'2008-09-02','The Pilgrimage paved the way to Paulo Coehlo\'s international bestselling novel The Alchemist. In many ways, these two volumes are companions—to truly comprehend one, you must read the other. Step inside this captivating account of Paulo Coehlo\'s pilgrimage along the road to Santiago. This fascinating parable explores the need to find one\'s own path. In the end, we discover that the extraordinary is always found in the ordinary and simple ways of everyday people. Part adventure story, part guide to self-discovery, this compelling tale delivers the perfect combination of enchantment and insight.','en','https://books.google.com/books/content?id=gn8emAEACAAJ&printsec=frontcover&img=1&zoom=1&source=gbs_api','Google Books',1,'2026-03-25 07:45:31','2026-05-12 06:10:00'),(67,'1212.1212',NULL,'gAAAAABp8XxA6K5AupUpKBF81dTunxmycCKOFkUKfvV-y8uRlfSuz2sI3CZQmwr37lKwFY9WlkZxypvBirUlvZ5hlAYp52ovLA==','gAAAAABp8XxAaeZUP775prhF8m4pJU5Qeo71_ssYIsI9VfjCB-9OjJeT6ktJ6vnvZygY_n4XyBpd1wrSJi76bqP9vgzMdH48kuvqnd-gAe5Xg7-tDbzBkXM=','db930c199680d7aa8466458c67dec8c219dde0009b09dfa529117a7517228616','gAAAAABp8XxAZz3nyss3NZe5THxQSTKgzO9zAEwZgI0szgBISnAEVUrpuaziyKbCe_4k2KPNRgDF7SgZkFNLPD7nLl06LzsIYg==','c5fc9fbd809389a9926dd9d7c32332161995f3623b1d9479cf23818f2d260ef8','gAAAAABp8XxAB24bxyovbJcLa2slEf1ieYyssvs4-m24BFFs1yswyfxnmAn7NVaXWXOwGSekABsnPqkmgROFTzMTE5Q6IgGsM1RLPC45kMbRJl94cT1vYMk=','9126a3c94a370f4d49303d761192bec66b56ad7cf04cfd9ee3fc856133ce6afb',NULL,256,'gAAAAABp8XxASD84yXn0Nw3gtp7z3zIA26xJ2F70nV_mwF071C5N-WfBdOenvjlG8GcHU7qWYY_8s8X-atBIGh3V2n4LOrJGlFWEFSp-SzvYXIPI8rCtXLc=','donation',100.00,'gAAAAABp8XxAvNWAWMiY2K0OR5CBfz3R1ctrk8FejnDEjQus77Ixe6flA4tYD8_9JBgJGGqT7UBj4a28SwKIJ_w99khX0VtsLA==','2026','..Hope you like it','2.3.2026','Enemies to lover and back to enemies','en','https://covers.openlibrary.org/b/id/15179814-M.jpg','Open Library',1,'2026-04-29 03:34:24','2026-05-12 06:10:00'),(69,'1212.1212','2026-04-25','gAAAAABp8cStrGLExd4MCt6DudlOfDvja9o5fGprYdy5_2aiyEp9G2RimI-OFx_JObyd8MzfWDXZbBm4_6rz70Fbn3I-6jUHIg==','gAAAAABp8cStw04Uv71RYpI5p1gxvmCu2YXclQeR33bCFywFDm5YD2WjZZ-RXI44_4u3ElaTAQJnYtnvIoJUqrQalh_Q6rEhAg==','5c2b134fa724ec36c49c1622e5e3059b4bf11867c699d3a7d2bcdf30087108c8','gAAAAABp8cStNPvqmcCays_MnhT5t5mApa28xwqoTstp1ZPJJpNBMXdTO1IMd73WTFnwrfIuDAkjg1e4HBg4QKyjvW5S4l-GXGgD0YoO8PKFzpwZqbw8QUcc3F6PLN-g28VprAo7XHti','fc43ee78e99d14963750dcf887536edc20443f4ee794f5956f950f80b7aa07e0','gAAAAABp8cStDYBI8lUeC-lxIw9S8RLbKlwpOIDKu9KR6yBEhUHnRSh1x6Rn07wDyutP5-hw84pCHxBSF7iZ6DZFhHPLSn8XmrDkAFNkuL9A9nzIaSVjcUA=','84683a5738fdc138fb9bfa0ac4afba0585c096b4aab5eef9fa673ed809089564','2nd',223,'gAAAAABp8cSt1gh-xJn9mz0aufcDh56JqdwZHqjZjBRhy1H15-rhIM6H3RNNwAdmPCuyDv3XiMUIM4sdTHraCKo5WZXzc2rBng==','donation',100.00,'gAAAAABp8cStbq5rzsyQ_tMifyhrXK-UyOwyuE8o1BcONIl5aDrt9mYNS9O8Dcrg7QTyT85Yw850_Kk4bojMzWGDamePrEqGmdvteGBXidWIxWmf6Yg95CM=','2026','Mandarin','1997','[back cover] \r\nHarry Potter thinks he is an ordinary boy - until he is rescued by an owl, taken to Hogwarts School of Witchecraft and Wizardry, learns to play Quidditch and does battle in a deadly duel. The reason... HARRY POTTER IS A WIZARD!','en','https://covers.openlibrary.org/b/id/7355968-M.jpg','Open Library',1,'2026-04-29 06:07:50','2026-05-12 06:10:00'),(70,'1212.1212','2026-04-30','gAAAAABp8cpTJg_autvBzIvVxhzUaQv0aJgLNHXH1zUXfdAw0vfs1J7rF3AcKuXC3RdYpGd-ow7LWukQuyJez9sRKY9lM1WKlA==','gAAAAABp8cpTMxNP7zzl4qaEuhxCCyyqNPl0nP8NBZvYJrBc-cqke45VqsMicoA6qqr8c9ulxvP6Oq7DYLxxjQWqCcx_icq8sYtZymPZsuZTh1S1VL7yMbg=','744af7bce472b5eab6b9832038b5d94422726ec36cba1e3ae6f39148c7c14be3','gAAAAABp8cpTvzmwh77glUdzuqrXl96070vG2yUChWNV-XuAPQpHejM4PrllM4w5fBvulK0dWBBluk3M3d2P2usbVvkmW2BbrESYFt-9l9N93SMfLC0XEMmCVhMu5fn5wnrS_dRro8Se','ed94ab4a46ef580d4f75ca38f2dabefccda82e99d6b3e560710125a83322bed2','gAAAAABp8cpTn267nQ2lUWa2XfAkMNfTvH1KyMW1NncSwq9J6R9oYbz5J9TzvdQdTcDtmkozxSBvOJppsXhnqeXcH8fXGOHEOxF4kRoAe4BLcKM8rKEblN0=','e3def11e29fc79b9a3c0abd81cac024d21f35a1fb55ec2d6934fb4d82a1c77ce','2nd',538,'gAAAAABp8cpTLdkCogQEqVzCPWYbZOA7KQyRgmgfHM32m2NWT9iLdi89I1EiC6o9lU4ZXxXFnU7i11dwuLVJvq8uTxXZOSAyurNJCv4iI7WTjmWc_viHXvU=','donation',20.00,'gAAAAABp8cpTGdK4CPipt9xZofFjIwnVm2uLjDj9f_0LUS0nGsh5F7NgslSM9ULNZL4TPAc1CTdIKCMi3rYWYk67oG56R9mflHevMmAIo8W86EqhhnLHF7s=','2026','Mandarin','2010-11-17','Intended for courses in IT security and information assurance, this textbook provides detailed practical information on a wide variety of topics relating to network and system security and information protection. Beginning with an in-depth discussion of the need for information security, current threats, and the development of security culture, topics discussed include access controls, security operations and administration, auditing and monitoring, response and recovery, cryptography, network and telecommunications security, information security standards, professional certifications, and governance and legal compliance. Chapters include illustrations, notes, summaries, and quizzes. --Publisher.','en','https://books.google.com/books/content?id=-agjhFspvFMC&printsec=frontcover&img=1&zoom=1&edge=curl&source=gbs_api','Google Books',1,'2026-04-29 09:07:31','2026-05-12 06:10:00'),(72,'1212.1212','2026-05-19','gAAAAABqCqpPuQLAF4MFYuKx3bVWACXcyP4SQOdcOuNGnFfy1MhNhhwhGtngINZU6ffxB7rjNHSeOxB0eRHvJ0-mtEIF1p2Vgw==','gAAAAABqCqpPTy_I0giqwb_WI_2_XPjTfJwsVWSLTCRGdy_T-0cbXOmO-MlAf49FWBu0j_m2ed0-lQnl1qbs02veRPe5j9jSWOLYsN4clewM99IaxMNcPKM=',NULL,'gAAAAABqCqpPCz5iKOlmhq05X0Vkc2lui67T4kMtCEWB5FgINTS88xurQsarfgPKKPoWo02FPifTcoRkbm2MzvVEdjZkWe6N3WmkAKMIHcT28exDuX39aaaePGQC8IJH1_5ezQRZ4Z0k-M6Y1zAWaTb3PTo_gLkA7g==',NULL,'gAAAAABqCqpPi2a-U06pNsraf1hgOGTbZVjQYCea-LQr6zGuCWssCuze-jgzqVoSVFcQCcy2OvVapQAt_ar7GhXsa6sWBOtvTg==',NULL,'2nd',200,'gAAAAABqCqpP25XD3LTx5MZk9QShwtndwaeMHnAoklR2l0j_xUkX3Lz_XIrK4LKl6Zs6vI3zr-BHXxw4304dzVK_DErOibKOnibSLx3xTdZWQdnYUsi_nUQ=','donation',100.00,'gAAAAABqCqpPaa5puccajJ5XOTnErSQpWT0Y6vGo9Q2pZ1YtvZOQg7S5B9X4Ug4a-GoLUnAA2FiMhQCTMbs1WNsTflDGmfUNIA==','2026','Markos\'s life','1997','According to the 1999 British Major Polar, he published in London in the new book of London, a book of Markos Malayalam.','en','https://covers.openlibrary.org/b/id/15128897-M.jpg','Open Library',1,'2026-05-18 05:57:35','2026-05-18 05:57:35');
/*!40000 ALTER TABLE `books` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `events`
--

DROP TABLE IF EXISTS `events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `events` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `event_date` date NOT NULL,
  `start_time` time DEFAULT NULL,
  `end_time` time DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `image` varchar(500) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `category` varchar(20) NOT NULL DEFAULT 'general',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `events`
--

LOCK TABLES `events` WRITE;
/*!40000 ALTER TABLE `events` DISABLE KEYS */;
/*!40000 ALTER TABLE `events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `library_card_books`
--

DROP TABLE IF EXISTS `library_card_books`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `library_card_books` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `card_id` int(11) NOT NULL,
  `book_id` int(11) DEFAULT NULL,
  `book_title` varchar(400) NOT NULL,
  `book_author` varchar(300) NOT NULL,
  `book_isbn` varchar(30) DEFAULT NULL,
  `quantity` int(11) NOT NULL DEFAULT 1,
  `added_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_lcb_card` (`card_id`),
  KEY `idx_lcb_book` (`book_id`),
  CONSTRAINT `library_card_books_ibfk_1` FOREIGN KEY (`card_id`) REFERENCES `library_cards` (`id`) ON DELETE CASCADE,
  CONSTRAINT `library_card_books_ibfk_2` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `library_card_books`
--

LOCK TABLES `library_card_books` WRITE;
/*!40000 ALTER TABLE `library_card_books` DISABLE KEYS */;
INSERT INTO `library_card_books` VALUES (46,20,NULL,'The Life of Justice The Path of Justice Malayalam evio','F. Scott Fitzgerald','1-56619-909-3',5,'2026-05-14 12:00:43'),(47,21,67,'SLEEPARALIS','F. Scott Fitzgerald','978-3-16-148410-0',1,'2026-05-14 13:31:47'),(48,21,66,'The Pilgrimage','Paulo Coelho','9780061687457',1,'2026-05-14 13:31:47');
/*!40000 ALTER TABLE `library_card_books` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `library_cards`
--

DROP TABLE IF EXISTS `library_cards`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `library_cards` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `card_type_category` enum('member','borrower') NOT NULL DEFAULT 'borrower',
  `user_id` int(11) DEFAULT NULL,
  `firstname` varchar(100) NOT NULL,
  `lastname` varchar(100) NOT NULL,
  `phone_number` varchar(100) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `date_issued` date NOT NULL,
  `date_return` date DEFAULT NULL,
  `renewal1_checked` tinyint(1) NOT NULL DEFAULT 0,
  `renewal1_date` date DEFAULT NULL,
  `renewal2_checked` tinyint(1) NOT NULL DEFAULT 0,
  `renewal2_date` date DEFAULT NULL,
  `card_type` varchar(20) DEFAULT NULL COMMENT 'city_govt | regular',
  `valid_until` varchar(200) DEFAULT NULL,
  `photo_path` varchar(500) DEFAULT NULL,
  `registered_by` int(11) DEFAULT NULL COMMENT 'users.id of admin/librarian who created this',
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `registered_by` (`registered_by`),
  KEY `idx_card_category` (`card_type_category`),
  KEY `idx_card_user` (`user_id`),
  KEY `idx_card_issued` (`date_issued`),
  KEY `idx_card_lastname` (`lastname`),
  CONSTRAINT `library_cards_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `library_cards_ibfk_2` FOREIGN KEY (`registered_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `library_cards`
--

LOCK TABLES `library_cards` WRITE;
/*!40000 ALTER TABLE `library_cards` DISABLE KEYS */;
INSERT INTO `library_cards` VALUES (20,'member',70,'gAAAAABqBUjr0xCfHisXlm_GoY_IOLQbSq2hkhH1Ft8IAWj39vVZA5d4zlgMxfmVc_E945yMhSksK-MwFmHK5H_SLzY26ry02Q==','gAAAAABqBUjrySi6ObpguoHmnySsEwikp2oDHYyqFBp869WwBADRkbOBUqXsd547q4RK1zjYLpwpS3YgE4VXYhrY-7wrotkyGg==','gAAAAABqBUjrIDu5DsJ7_odLEuO-5rhhAYBVUJzFBsO6_6SpO9RLyrY8377H-PWm5KBOFGsgtSBrCUfOSB-uV9fFHAgDwl54jQ==','gAAAAABqBUjrEl20U4Qe55CtSWmqfW7IcLVewSCPKh1HxZhu1l1uloB7OQl1PbQhrvkDbDUN9vfl5paRtWXBJyE7lXw7WZI8BQ==','2026-05-14','2026-05-15',0,NULL,0,NULL,'regular','May 14, 2027','static/uploads/card_photos/member_46041b28bfee42e8a90a6bedbbec9910.jpg',1,'2026-05-14 12:00:43','2026-05-14 12:00:43'),(21,'member',75,'gAAAAABqBV5DTMcXdb-rBdapZp1FCEw0ZiCYau9ou0OMhKEQMRMWqnznGFoksNxLnuOhJ1qW4cYg97tLLTz4eelmELUWSXT_jw==','gAAAAABqBV5DURMhv1a-HDixQoFdSwQsy14tosF4lqVMGlIoPBkwJx8ekLWPFkqlhi6elB_NnFkjG8WTdUsrDzREkGEGFmvFcw==','gAAAAABqBV5DSGQl6SNFy6WWYN78_8m6cKfH0GgG2MMTw8MeAHtxPEjCxoJdOxDPjtp7S8dS_m2Mz374dp6viqhY94Yvv_nKeQ==','gAAAAABqBV5DU1BWOeSlYnZxKcv8ccYLuYPO0nxbxmMAdv7xi7oQLwZeBj_U5Ex-SJ5twhncrFg01i3eyDI2gJqM-ax8ZKf-XPmXeyfc76M2DoDBRVYK7DQ=','2026-05-14','2026-05-21',1,'2026-05-14',0,NULL,'regular','May 14, 2027','static/uploads/card_photos/member_0d2d68d3d1d14e0b8bb5b2609fdd24aa.webp',1,'2026-05-14 13:31:47','2026-05-14 13:33:36');
/*!40000 ALTER TABLE `library_cards` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notification_reads`
--

DROP TABLE IF EXISTS `notification_reads`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `notification_reads` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `announcement_id` int(11) NOT NULL,
  `read_at` datetime DEFAULT current_timestamp(),
  `dismissed` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_read` (`user_id`,`announcement_id`),
  KEY `announcement_id` (`announcement_id`),
  CONSTRAINT `notification_reads_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `notification_reads_ibfk_2` FOREIGN KEY (`announcement_id`) REFERENCES `announcements` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=820 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notification_reads`
--

LOCK TABLES `notification_reads` WRITE;
/*!40000 ALTER TABLE `notification_reads` DISABLE KEYS */;
INSERT INTO `notification_reads` VALUES (787,70,2,'2026-05-12 14:36:15',0),(788,70,3,'2026-05-12 14:36:15',0),(789,70,4,'2026-05-12 14:36:15',0),(790,70,5,'2026-05-12 14:36:15',0),(791,70,6,'2026-05-12 14:36:15',0),(795,70,70,'2026-05-12 14:36:15',0),(797,75,5,'2026-05-14 13:35:41',0),(798,75,2,'2026-05-14 13:35:41',0),(799,75,3,'2026-05-14 13:35:41',0),(800,75,4,'2026-05-14 13:35:41',0),(802,75,6,'2026-05-14 13:35:41',0),(803,75,77,'2026-05-14 13:35:41',0),(805,75,70,'2026-05-14 13:35:41',0),(806,75,78,'2026-05-14 13:35:41',0),(807,75,79,'2026-05-14 13:35:41',0),(808,70,77,'2026-05-14 14:37:04',0),(819,70,80,'2026-05-20 14:26:14',0);
/*!40000 ALTER TABLE `notification_reads` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `qr_login_tokens`
--

DROP TABLE IF EXISTS `qr_login_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `qr_login_tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `token` varchar(64) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `status` enum('pending','confirmed','expired') NOT NULL DEFAULT 'pending',
  `created_at` datetime NOT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `qr_login_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=82 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `qr_login_tokens`
--

LOCK TABLES `qr_login_tokens` WRITE;
/*!40000 ALTER TABLE `qr_login_tokens` DISABLE KEYS */;
INSERT INTO `qr_login_tokens` VALUES (81,'y7QKG1u4TtmxZmynb-d0qXyfPhb-d8-EBuJ4IW4QBiY',NULL,'pending','2026-05-17 18:51:20','2026-05-17 18:52:20');
/*!40000 ALTER TABLE `qr_login_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system_settings`
--

DROP TABLE IF EXISTS `system_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_settings` (
  `id` int(11) NOT NULL DEFAULT 1,
  `maintenance_enabled` tinyint(1) NOT NULL DEFAULT 0,
  `maintenance_message` text DEFAULT NULL,
  `bypass_role` varchar(30) NOT NULL DEFAULT 'admin',
  `lockdown_enabled` tinyint(1) NOT NULL DEFAULT 0,
  `backup_frequency` enum('hourly','daily','weekly','monthly','off') NOT NULL DEFAULT 'weekly',
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_settings`
--

LOCK TABLES `system_settings` WRITE;
/*!40000 ALTER TABLE `system_settings` DISABLE KEYS */;
INSERT INTO `system_settings` VALUES (1,0,'The library system is currently under scheduled maintenance. We\'ll be back shortly. Thank you for your patience.','admin',0,'weekly','2026-05-30 12:31:25');
/*!40000 ALTER TABLE `system_settings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_appearance`
--

DROP TABLE IF EXISTS `user_appearance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_appearance` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `theme` varchar(20) NOT NULL DEFAULT 'ocean',
  `language` varchar(20) NOT NULL DEFAULT 'english',
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `user_appearance_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=242 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_appearance`
--

LOCK TABLES `user_appearance` WRITE;
/*!40000 ALTER TABLE `user_appearance` DISABLE KEYS */;
INSERT INTO `user_appearance` VALUES (215,70,'midnight','english','2026-05-16 20:21:14');
/*!40000 ALTER TABLE `user_appearance` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_favorites`
--

DROP TABLE IF EXISTS `user_favorites`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_favorites` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `book_id` int(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_fav` (`user_id`,`book_id`),
  KEY `book_id` (`book_id`),
  CONSTRAINT `user_favorites_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_favorites_ibfk_2` FOREIGN KEY (`book_id`) REFERENCES `books` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=74 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_favorites`
--

LOCK TABLES `user_favorites` WRITE;
/*!40000 ALTER TABLE `user_favorites` DISABLE KEYS */;
INSERT INTO `user_favorites` VALUES (69,73,70,'2026-05-10 13:29:53'),(71,75,66,'2026-05-17 18:48:47');
/*!40000 ALTER TABLE `user_favorites` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_search_history`
--

DROP TABLE IF EXISTS `user_search_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_search_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `query` varchar(255) NOT NULL,
  `searched_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_user_search` (`user_id`,`searched_at`),
  CONSTRAINT `user_search_history_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_search_history`
--

LOCK TABLES `user_search_history` WRITE;
/*!40000 ALTER TABLE `user_search_history` DISABLE KEYS */;
INSERT INTO `user_search_history` VALUES (41,70,'Harry Potter and the Philosopher\'s Stone','2026-05-04 11:35:27'),(42,70,'scott','2026-05-12 13:48:03'),(43,70,'fic','2026-05-12 14:11:33'),(44,70,'Classic Fiction','2026-05-12 14:11:45'),(45,70,'class','2026-05-12 14:12:06'),(46,70,'978-3-16-148410-0','2026-05-12 14:12:19'),(47,70,'Classic Fiction','2026-05-12 14:14:09'),(48,70,'class','2026-05-12 14:14:38'),(49,70,'classic','2026-05-12 14:14:40'),(50,70,'classic fiction','2026-05-12 14:14:43'),(51,70,'The Life of Justice The Path of Justice Malayalam evio','2026-05-16 20:17:01');
/*!40000 ALTER TABLE `user_search_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `email_display` text DEFAULT NULL,
  `firstname` varchar(255) DEFAULT NULL,
  `lastname` varchar(255) DEFAULT NULL,
  `name_index` varchar(64) DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `failed_attempts` int(11) DEFAULT 0,
  `is_locked` tinyint(1) DEFAULT 0,
  `lock_until` datetime DEFAULT NULL,
  `otp_code` varchar(255) DEFAULT NULL,
  `otp_expiry` datetime DEFAULT NULL,
  `status` varchar(10) DEFAULT 'offline',
  `last_seen` datetime DEFAULT NULL,
  `role` enum('user','librarian','admin') DEFAULT 'user',
  `phone_number` varchar(255) DEFAULT NULL,
  `phone_index` varchar(64) DEFAULT NULL,
  `reset_token` varchar(255) DEFAULT NULL,
  `reset_token_expiry` datetime DEFAULT NULL,
  `age` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `is_approved` tinyint(1) NOT NULL DEFAULT 0,
  `otp_enabled` tinyint(1) NOT NULL DEFAULT 0,
  `pin_enabled` tinyint(1) NOT NULL DEFAULT 0,
  `pin_code` varchar(255) DEFAULT NULL,
  `pin_set_at` datetime DEFAULT NULL,
  `pin_reset_token` varchar(255) DEFAULT NULL,
  `pin_reset_token_expiry` datetime DEFAULT NULL,
  `gender` varchar(512) DEFAULT NULL COMMENT 'PII-encrypted (PII_ENCRYPTION_KEY)',
  `school` varchar(512) DEFAULT NULL COMMENT 'PII-encrypted',
  `city` varchar(512) DEFAULT NULL COMMENT 'PII-encrypted',
  `province` varchar(512) DEFAULT NULL COMMENT 'PII-encrypted',
  `education_level` varchar(512) DEFAULT NULL COMMENT 'PII-encrypted',
  `occupation` varchar(512) DEFAULT NULL COMMENT 'PII-encrypted',
  `is_government` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Plain 0/1 flag — not PII',
  `office_phone` varchar(512) DEFAULT NULL COMMENT 'PII-encrypted',
  `valid_id_path` varchar(512) DEFAULT NULL COMMENT 'PII-encrypted vault path — never a public URL',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_name_index` (`name_index`),
  KEY `idx_phone_index` (`phone_index`)
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'5073a76312c946492b53841c1af2485db0cfa53f5cad9367c41e2a7ac6d80f3d','gAAAAABp3F9R23R8Rw9Ut0mr6R2ORJdreE2y-7F0jJAj05Gjuj6HcbR1Md5yeOIAb0tzh93ALGrhOcucQj-9adjsqUls5xg2jZ9v3oCsKGTBhGMFK9YyC-o=','gAAAAABp3FvvNuf0jQGAFcqSVAaf6alX19y0Xh0bjyrlaDIvQclqq67wI9H19W0vu_P0T9f_-GG_ydmlv_xEYSiVmUe0BfF7_g==','gAAAAABp3FvvMbIQMyGfJ0Kb54WWS1aC5zGLuhZhK8-5-Pd0hcvx4RvfJR23RfkR6--JKu1XWzu5nUs828Miu9hhcvxD8V-doA==','5c2b134fa724ec36c49c1622e5e3059b4bf11867c699d3a7d2bcdf30087108c8','$2b$12$3se/EaZkjN5418Pnto1PUOfKqPG5npihe4W0MKpaKaAXAiC54sYm6','2026-01-02 06:24:12',0,0,NULL,NULL,NULL,'active','2026-05-30 13:56:06','admin',NULL,NULL,NULL,NULL,NULL,1,1,1,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL,NULL),(70,'faf7cfd842a3465e5f5e4e30c2174d29978c5fad3b16300fdcd5745f0320fafd','gAAAAABp-A1xwAeNoZnJqfl1rBpKZGkIStSC8K-sWdffcxiqqiEf-n_Da1aDwZJhNWQZR3L6ZV23MMu3Mk3aQZtmS3X2krpTZ7oOoqObPGmMrS8B_zaYWtA=','gAAAAABp-A1yijru5AqAfk_cuPHzyGKDKojA6sxhbMG2B-duxLh2aOBCh_Ybb09oqxOFi_a5U5cC0j8x_JsO17HtwgD7PTybkA==','gAAAAABp-A1yyzBnXVOI9fG-jDLDeAaMMyAXgcmuUWZglAJga2BFhCuD__mTMcNBlqXYS1cYdOopomqEhQciF7bUiuGUpCSCtg==','5c2b134fa724ec36c49c1622e5e3059b4bf11867c699d3a7d2bcdf30087108c8','$2b$12$HrV05TCR8Bu1qVbCgjhyfOKE9gbSSjjnBfdvHQDmHuhtjXDgGKt.C','2026-05-04 03:07:30',0,0,NULL,NULL,NULL,'active','2026-05-29 18:50:54','user','gAAAAABp-A1yicYeDoJVrrCwJA4rjalss_oCgb-5mvWsQrEwZlWGUlS4tfwaa_haj9I5fxotVfZ7wJrpDzsTQ7Up8SD5x8dasw==','4c90ff5c450e801ec8d5b1bdda1e832df07ce74d20bd4e7a9c014e6eaa4e0f2b',NULL,NULL,'gAAAAABp-BEWaVRU6b_Bv1DDQSd3KP2ozJOulfER3DshSnksR4teQ5_rQNC3ZbSL5Pl__AxvL5azgMccFlGEVUSp8j642NS7Mw==',1,1,0,0,'$2b$12$zTk.daJTXP.HyadXsGF9.eZVoPDHsrklgJGahzrQSPiq.aT/D38yu','2026-05-09 11:30:20',NULL,NULL,'gAAAAABp-A1yIrvXw9ZqEEsmE0eABf7wgU-54C_d6tYljFEv1kGl1n2qPYecblmHCFvjI4EWO4QzhTdZChyIUV3cEosskiNljw==','gAAAAABp-A1yjKv3U-5rCIdacMa-N76kK9x6areLBRqoDY386Vg1dQtY0dQXyKhqDiLDMfSHFTpQ7Vg9ECm2_Lk7F6goDrKsBA==','gAAAAABp-A1y6hn48mEpcKFAXyjkt5lVuM2esZ8MAIQQlv6_8EbtR4JGKcTX03fGbv6BbznuhhbVczYU50lRnswkXdQ5_iUWdQ==','gAAAAABp-A1yld-gLG6rvQZRdJg4vI71CNadTb3pr2XO4SMjsNPVBw3ZphuNAaDhdKc3WijkOV6uDBa_zs437ZB1jXPuT3a4Mg==','gAAAAABp-A1yWcAclgjNIN_Gcxt0mgRzD7XSlyJzumbhzgtK4fqtf5v7XTETaO06Ft-YYyBbsejf6AogAYzISd8NxykgKxTytIBvDs-DiOHfaScblsKQp2A=',NULL,0,NULL,'gAAAAABp-A1xe3A6KI5acNCrYcI4UWaF3o3rskKDUpWE6CtwX3hPi-VfIyfUBU2LaI66FYni2ddjd2pFrquUSSDHKX0HnWrOlD3NBKBzBBNXAeazrE-bAUkCqkQPuouQO-i6-baAVKhVayl2Ij7hjG4ZtbSJY2V1eOHKdKmvpZ_T3HIBTYEGOe4z6HV8DXUkGlwLGxEeoVU7ndJbhNtDJed7A1tFa4AcW7jbJgeRyJh_uBWqfOMJAomeyttaARvGFl3O7qgIJF46'),(73,'128d8758524723c62e95cd4d547ad26b409077f48d51540726c340608217000d','gAAAAABqABchRJS_vFpTSLxTE7nSzVFechTXKjVLN9Z-YoZjUg6UfgrxZVaR4U1z22yLp4U0UzOzWpv1VbeiLCCYBlaqFg7T9SbOELdNU9yJtQ9rwb_3MvA=','gAAAAABqABch12T_2AMznHCECHAtqIiyMiVDELPnHRBw8vjCsuLEL6cP1fKDNOAKFsePWCtLJOaIL2aCmBj386qeAQwSpDzkIQ==','gAAAAABqABchi4K2tWcB3ceDuwPVhN9p7uGVE39zgGHX6nPVcedEN3-jla2CL178zH5zT5U1a53mXin1nPreDj_H94kdq1z1Nw==','19bf1df5c36c06bff42af24eb14c834244abf10c2772ecd687f0cc711107cb13','$2b$12$OdSvc1S/wmrm9EuaEmq5l.yJaC37UN9hOjeQZPqzhjsVPjBzgqS7.','2026-05-10 05:26:57',0,0,NULL,NULL,NULL,'active','2026-05-10 13:30:13','user','gAAAAABqABchWy3oaIEBpgL8onacD3x6udubqSPcPoylR3PG-aZQqJJ69BpM2A6ImvhrZ7q4ZHXahZlNvaG2SVCXOwMnVENLeQ==','5904d817161dba47ba9be387f677d2d339326168c4dadbf5552321470567104d',NULL,NULL,'gAAAAABqABch56h7cPzn7jGTQhfaRZytzcxEOR7goXn6FXgEZQkutwmM7kLPmLN6H2Z-tQzDCN6YKSWlzLs1vJue6pXMFZi7yg==',1,1,0,0,NULL,NULL,NULL,NULL,'gAAAAABqABchOvdO0dt7sLAw2L4ANXkJqX734p3iaphXCxND5qBNcA1Pa5QoWLmT3rSllRqwwtaImnZ5Egpkz8h1HLhs-qeWuw==','gAAAAABqABch3U4jpX6vrrHulKCQSiGQdwpxdgtP_CHK6MXVnzHvmDOAmZsWHfGRrp_BZznNr8co5_bvcyt8CQ2p1nIcIQl34u7XdJlQ04OBqlC6qGlRDsk=','gAAAAABqABchGxHfbSKGcCFswHF_8V5nNJYEg1yA98d8KEJOF4Kt8ReO1sHeJr_YLuZYZFTSATMVCeERFuOjL2t0_9QVeHZN_w==','gAAAAABqABchkLZfIPy-LnDibYfqGZXOaHZB592ulwKNYAPqCVPYvs4HaB-CfaMwf00FKIYZGWlkl02AexYX8JRZzIWVf26FGg==','gAAAAABqABchgUY8VT17ZerOhXRWvzwq0yhri0r5fUKXaRdJE8ZYJl_OKsPC8Z0coqpQ-dV6NdXR-bHMQ-HBq29hUcVkGPqeVw==',NULL,0,NULL,NULL),(74,'d9b01a1072892ff2c48081c300c751b10fbd0915671064500f854d24fe3074a7','gAAAAABqAY9x1t4PHKCy3cWF17qdz-uPz820W5Fw2tU4AZYQUfsGJ1GF37U2aokiakN5TrA4JjYAhrJkIgPqLJp1XZ2MutChO9HHQs7dYo2Ewts6oEAQDQs=','gAAAAABqAY9xW797mqV4-JePUHSW2ynqbH_RVZqsYUs3TXtQ37aHTVZHNjplLhH297AIP0Lwd1Oh3GhDJTZYirxUsn3dw3uAig==','gAAAAABqAY9xvsk0pA8ZKyhdQRTYRenrcAC47ZCAstEWbJWKCww1qb_FsFgWur3Vp_IotELeawYZPQwtI912wmZ_0ID5bmMHTw==','f250a845a4438eb9005ccfbc6066a587fe93f7e3cfc3e847c0344d75eba52c64','$2b$12$igC3v25Lo/N5OB1BDCxk8uvNoUeJ2XN3s4pchi4BmbWeRnoXOT5SG','2026-05-11 08:12:33',0,0,NULL,NULL,NULL,'offline',NULL,'admin',NULL,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL,NULL),(75,'fc2f85a9d1e8c4b14e4f0ab402e59967d37ae8cbae9534ab0bbfac843a427da7','gAAAAABqBVyuBJ8DsEQhstaUbWIVMziI33CayGH0OAV-eqW0ON9LLQeXIZ2Vigdv8QPQb5ggB8PxMkKzFlhYQU73Bq9rItokhQvFmTtApsma1ieLRmiJTZk=','gAAAAABqBVyu_xckEtbWac-WrSzv8UC9c1_uJmRJoPBNVWCwz9OtVLTMwqkmip5C0oJ-JzNYf-PaXjhCPtknMJcQqg3SHT3PMQ==','gAAAAABqBVyuxMBUFtSit3F3quYHVwq6nPnSMb6ZlN_2v9z5vfz4b0WJs4K4OzuV8AbF5Ic9EKBkPAzdy4-8QomajRXs5h5dbg==','811284c536e20baa3f5a0a1f665a790381447e9e63850373e42f1c18d253200f','$2b$12$fKZDfPPllSE9.wMU9B7VmeT49ifmgFGaEkHAsar57zyzdHNF1p5Zu','2026-05-14 05:25:02',0,0,NULL,NULL,NULL,'offline','2026-05-17 18:50:37','user','gAAAAABqBVyuhI0QPoQw-W13duGZKQVoFQYALu0QOjR9FNlNOuDbrKMIfhNIyUZgJBb_I-j6j2UT5ETVXktQvNDYdqV2GiE8wg==','2a9208f077548cc484eb65e71c0c3f47b1252fdac8769df57db00f8c1cff1779',NULL,NULL,'gAAAAABqBV2hzespJ9pCqOE786VSToriiv_7RKo4U68JNPiTiT7hBx2WiDWJjhUHnR_VZuJf6i9dN-AyKy5YUukpS7BV_-Q0VQ==',1,1,0,0,NULL,NULL,NULL,NULL,'gAAAAABqBVyuEiQiReDCH-vdlhhLEfrx1qR7On1BFU5nhfvTNLeclOn7tft9NsP-LdmHY7vxro0ZiCLm9_DED6TYpCKT48SHNA==','gAAAAABqBVyuUV-oysoYyQXcKW5W06f6buBR65u2vWzDdeoA-DP78RDbF1-HbCeOzH5EM-RzRwZ2bpbRqcHGSliUzO-9OscOi5bxeYcdeRqNpPCyWVNt2Pg=','gAAAAABqBVyuvemsfhzyJGDA0ZJs09F9vf_bYkMh4pPcEilTEpzfHUyy4jShLT8q7iOIONdwkL8YQ-M1nAfwndrZ116WeUuuHg==','gAAAAABqBVyuHfI3if7UMkuFWtVBaGc-FN1g7Dd29th69m6-SZNK_CTl7rQvP0m_eupH_k6ILrotA7mXSfSH74iXcCSac_tdUA==','gAAAAABqBVyux2t5o0Ug6OEOYXx9MGURtGROcEjd8QemAC470nLzUu50UVrc3eFfIatkW0Z_1Vbe8eE1JQkfiUCIzOdFzFTlWg==',NULL,0,NULL,NULL),(76,'070ae3b1aa7cac5e9c465c3cb6e47aafb727881e27656e156dd1d3cdb4ebb167','gAAAAABqCcZFWrhfk-fKbC_Nzfe3R3_9CuXRAS7Sjr9nxuUt1q_N0olDuM05fmaGzsmpJPtEfR9aeOE5ftIOj4Sr4AxeaNAiismZEnYz9DFgZmyQRLiItwo=','gAAAAABqCcZFYZ5KzVcMKe98nW3rd3mU-PMyz0Hc3wUYg1RFwxFnMiH5cKhGxLHPShpiVL1Bn5xLyU8I5fttI4BChNot05NPBQ==','gAAAAABqCcZFdINCrqy3XnJ9TYNOUkH2TqKuj0KMuSN-8LnigKBpCABvYbtnFcGuZgkIX_Cc_DRmCZVoPEx30fVjZvsJjNPWqg==',NULL,'$2b$12$ODKIEEPAeqy169fpOhP0xuOmTNjSKOEOTaA47kT2AW6mNPQcTYEDG','2026-05-17 13:44:37',0,0,NULL,NULL,NULL,'active','2026-05-20 18:41:17','librarian',NULL,NULL,NULL,NULL,NULL,1,1,0,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,0,NULL,NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 's-premium'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-30 13:56:06
