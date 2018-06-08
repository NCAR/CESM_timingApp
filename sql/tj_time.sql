--
-- Table structure for table `t_timeMaster`
--
USE csegdb;

DROP TABLE IF EXISTS `tj_time`;
CREATE TABLE `tj_time` (
  `comp_id` integer NOT NULL,
  `master_id` integer NOT NULL,
  `comp_pes` integer NOT NULL,
  `root_pes` integer NOT NULL,
  `tasks_threads` varchar(20) NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=26 DEFAULT CHARSET=latin1;
