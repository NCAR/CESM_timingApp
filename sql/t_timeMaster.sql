--
-- Table structure for table `t_timeMaster`
--
USE csegdb;

DROP TABLE IF EXISTS `t_timeMaster`;
CREATE TABLE `t_timeMaster` (
  `id` integer NOT NULL AUTO_INCREMENT,
  `machine` varchar(20) DEFAULT NULL,
  `resolution` varchar(30) DEFAULT NULL,
  `compset` varchar(30) DEFAULT NULL,
  `total_pes` integer DEFAULT NULL,
  `cost` float DEFAULT NULL,
  `throughput` float DEFAULT NULL,
  `file_date` DATETIME DEFAULT NULL,
  `cesm_tag` varchar(30) DEFAULT NULL,
  `comments` varchar(256) DEFAULT NULL,
  `user_id` varchar(30) DEFAULT NULL,
  `timing_file` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=26 DEFAULT CHARSET=latin1;
