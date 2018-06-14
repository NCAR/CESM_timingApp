#!/usr/bin/env perl
# removeTiming.pl
#
# remove a timing entry from the database
# usage : removeTiming.pl time=[t_timeMaster_id]
#

use warnings;
use strict;
use DBI;
use DBD::mysql;
use lib qw(.);
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser warningsToBrowser); 

use lib "/home/www/html/csegdb/lib";
use config;

# Get the necessary config vars for the database
my %config = &getconfig;
my $version_id = $config{'version_id'};
my $dbname = $config{'dbname'};
my $dbhost = $config{'dbhost'};
my $dbuser = $config{'dbuser'};
my $dbpasswd = $config{'dbpassword'};
my $dsn = $config{'dsn'};

my $dbh = DBI->connect($dsn, $dbuser, $dbpasswd) or die "unable to connect to db: $DBI::errstr";

my $time_id = param('time');

if (!defined($time_id)) { 
    die("No time_id specified. Usage : removeTime.pl time=[t_timeMaster_id]"); 
}
#
# delete from the t_time* tables
#
my $sql = qq(select count(id) from t_timeMaster where id = $time_id);
my $sth = $dbh->prepare($sql);
$sth->execute() or die $dbh->errstr;
my ($count) = $sth->fetchrow;
$sth->finish;

if ($count > 0) {
    # delete from the tj_time table
    $sql = qq(delete from tj_time where master_id = $time_id);
    $sth = $dbh->prepare($sql);
    $sth->execute() or die $dbh->errstr;
    $sth->finish;

    # delete from the t_timeMaster table
    $sql = qq(delete from t_timeMaster where id = $time_id);
    $sth = $dbh->prepare($sql);
    $sth->execute() or die $dbh->errstr;
    $sth->finish;
}

$dbh->disconnect;

exit 0;
