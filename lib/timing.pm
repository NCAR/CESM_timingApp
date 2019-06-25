package timing;
use warnings;
use strict;
use DBI;
use DBD::mysql;
use Time::localtime;
use DateTime::Format::MySQL;
use Array::Utils qw(:all);
use vars qw(@ISA @EXPORT);
use Exporter;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser); 
use CGI::Session qw/-ip-match/;
use lib "/home/www/html/csegdb/lib";
use config;

@ISA = qw(Exporter);
@EXPORT = qw(getTimings getUserName getCompiler getMpilib);

sub getTimings
{
   my $dbh = shift;
   my @timings;

   my $sql = qq(SELECT *  FROM t_timeMaster);
   my $sth = $dbh->prepare($sql);
   $sth->execute();
   while(my $ref = $sth->fetchrow_hashref())
   {
       my %timing;
       $timing{'id'} = $ref->{'id'};
       $timing{'machine'} = $ref->{'machine'};
       $timing{'resolution'} = $ref->{'resolution'};
       $timing{'compset'} = $ref->{'compset'};
       $timing{'total_pes'} = $ref->{'total_pes'};
       $timing{'cost'} = $ref->{'cost'};
       $timing{'throughput'} = $ref->{'throughput'};
       $timing{'file_date'} = $ref->{'file_date'};
       $timing{'cesm_tag'} = $ref->{'cesm_tag'};
       $timing{'comments'} = $ref->{'comments'};
       $timing{'timing_file'} = $ref->{'timing_file'};
       ($timing{'firstname'}, $timing{'lastname'}) = &getUserName($dbh, $ref->{'user_id'});
       $timing{'compiler'} = &getCompiler($dbh, $ref->{'compiler_id'});
       $timing{'mpilib'} = &getMpilib($dbh, $ref->{'mpilib_id'});

       # get the component timing data
       my $sql1 = qq(SELECT c.name,j.comp_pes, j.root_pes, j.tasks_threads FROM
                     tj_time as j, t_timeComponent as c, t_timeMaster as m
                     WHERE m.id = j.master_id 
                     AND c.id = j.comp_id
                     AND m.id = $timing{'id'});
       my $sth1 = $dbh->prepare($sql1);
       $sth1->execute();
       my %compTime;
       while(my $comp = $sth1->fetchrow_hashref())
       {
	   my $name = $comp->{'name'};
	   $compTime{$name}{'name'} = $name;
	   $compTime{$name}{'comp_pes'} = $comp->{'comp_pes'};
	   $compTime{$name}{'root_pes'} = $comp->{'root_pes'};	   
	   $compTime{$name}{'tasks_threads'} = $comp->{'tasks_threads'};
       }
       $sth1->finish();
       $timing{'compTimes'} = \%compTime;
       push(@timings, \%timing);
   }
   $sth->finish();
   return @timings;
}

sub getUserName
{
   my $dbh = shift;
   my $user_id = shift;

   my $sql = qq(SELECT count(user_id), firstname, lastname from t_svnusers 
                WHERE user_id = $user_id);
   my $sth = $dbh->prepare($sql);
   $sth->execute();
   my ($count, $firstname, $lastname) = $sth->fetchrow();
   $sth->finish();

   if ($count) {
       return $firstname, $lastname;
   }
   else {
       return ('Unknown','');
   }
}

sub getCompiler
{
   my $dbh = shift;
   my $compiler_id = shift;

   my $sql = qq(SELECT count(name), name from t_compiler
                WHERE compiler_id = $compiler_id);
   my $sth = $dbh->prepare($sql);
   $sth->execute();
   my ($count, $name) = $sth->fetchrow();
   $sth->finish();

   if ($count) {
       return $name;
   }
   else {
       return 'Unknown';
   }
}


sub getMpilib
{
   my $dbh = shift;
   my $mpilib_id = shift;

   my $sql = qq(SELECT count(name), name from t_mpilib
                WHERE mpilib_id = $mpilib_id);
   my $sth = $dbh->prepare($sql);
   $sth->execute();
   my ($count, $name) = $sth->fetchrow();
   $sth->finish();

   if ($count) {
       return $name;
   }
   else {
       return 'Unknown';
   }
}
