--
-- Table structure for table `t_timeMaster`
--
USE csegdb;

DROP TABLE IF EXISTS `t_timeComponent`;
CREATE TABLE `t_timeComponent` (
  `id` integer NOT NULL AUTO_INCREMENT,
  `name` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=26 DEFAULT CHARSET=latin1;
