#!/usr/bin/env perl

use warnings;
use strict;
use CGI qw(:standard);
use CGI::Session qw/-ip-match/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser); 
use DBI;
use DBD::mysql;
use Time::localtime;
use HTML::Entities;
use Data::FormValidator;
use Data::Dumper;
use Template;
use Template::Plugin::SSI;
use Template::Plugin::Dumper;
use lib "/home/www/html/csegdb/lib";
use config;
use session;
use user;

Log::Log4perl->init("../conf/timing-log.conf");
my $log = Log::Log4perl->get_logger();



#------
# main 
#------
$ENV{PATH} = '';

my $req = CGI->new;
my %config = &getconfig;

#
# Month Conversion quick lookup
#
my %mon2num = qw(
    Jan 01  Feb 02  Mar 03  Apr 04  May 05  Jun 06
    Jul 07  Aug 08  Sep 09  Oct 10  Nov 11  Dec 12
);

#
# Names of all components in use
#
my %cpl = ();
my %atm = ();
my %lnd = ();
my %ice = ();
my %ocn = ();
my %rof = ();
my %glc = ();
my %wav = ();
my %esp = ();

#
# DB config info
#
my $dbname = $config{'dbname'};
my $dbhost = $config{'dbhost'};
my $dbuser = $config{'dbuser'};
my $dbpasswd = $config{'dbpassword'};
my $dsn = $config{'dsn'};

# Check the session, see if it's still valid. This will redirect to login page if needed.
my ($loggedin, $session) = &checksession($req);
my $cookie = $req->cookie(CGISESSID => $session->id);
my $sid = $req->cookie('CGISESSID');

# define the results and formValidator objects
my ($dfv_profile, $results);

my %item = ();
my $tmpl   = "../templates";
my $dbh = DBI->connect($dsn, $dbuser, $dbpasswd) or die "unable to connect to db: $DBI::errstr";

#
# get the logged in user info loaded into the item hash
#
$item{luser_id} = $session->param('user_id');
$item{llastname} = $session->param('lastname');
$item{lfirstname} = $session->param('firstname');
$item{lemail} = $session->param('email');

if ($loggedin == 1) { 
    &doactions(\$req);
}
else {
    $dbh->disconnect;
    print $req->header(-cookie=>$cookie);
    print qq(<script type="text/javascript">
              alert("Only SVN developers of UCAS logins are allowed to upload CESM timing files.");
              window.close();
             </script>);
     exit 0;
}

#---------
# end main
#---------

# decide what to do based on the passed in action value

sub doactions
{
    my $action = $req->param('action') || '';

    $item{message} = $req->param('message') || '';

    if( length($action) == 0 )
    {
	&uploadForm;
    }

    if ($action eq 'uploadProc') 
    {
	my $validated = &validateRequest($req);
	if( $validated == 1 )
	{
	    &uploadProcess;
	}
	else 
	{
	    &uploadForm;
	}
    }
}

#------------------
# uploadForm
#------------------

sub uploadForm
{
#
# load up the vars hash to pass to the template
#
    my $vars = {
   };

    $dbh->disconnect;

    print header;
    #my $tmplFile = '../templates/uploadForm.tmpl';
    my $tt_template = "form.tt";

    my $template = Template->new({
	ABSOLUTE => 1,
	EVAL_PERL => 1,
	INCLUDE_PATH => '/home/www/html/timing/templates'
				 });

    $template->process($tt_template, $vars) || die ("Problem processing $tt_template, ", $template->error());
}

#--------------------
# validateRequest
#--------------------

sub validateRequest
{
    $item{message} = '';
#
# define the required fields for the validator
#
    $dfv_profile = {
	'required' => [ qw( file cesm_tag compset resolution update comments ) ],
    };

    $results = Data::FormValidator->check( $req, $dfv_profile );

    if ( $results->has_missing )
    {
# 
# missing fields
# 
	$item{message} = qq( The following required fields are missing:<br> );
	for my $f ( $results->missing ) 
	{
	    $item{message} .= qq($f<br>);
	}
	return 0;
    }

    if( length($item{message}) > 0 ) {
	return 0;
    }
#
# everything looks ok, return for processing in the DB
#    
    return 1;
}

#----------------------
# uploadProcess
#
# Begin Upload Process
#----------------------

sub uploadProcess
{
    #
    # build up the SQL insert statement for a new account with pending approval request 
    #
    for my $f ( $results->valid() ) {
	$item{ $f } = $results->valid( $f );

    }
    #
    # upload and parse timing file here...
    #
    &uploadAndParse;

    #
    # load up SQL statements from parsed timing file
    #
    my $master_id;
    my $comp_id;
    my $components = "cpl|atm|lnd|ice|ocn|rof|glc|wav|esp";
    my @componentarray = (\%cpl,\%atm,\%lnd,\%ice,\%ocn,\%rof,\%glc,\%wav,\%esp);

    #
    # Preping values for SQL insertion
    #
    my $qcompset    = $dbh->quote($item{compset});
    my $qresolution = $dbh->quote($item{resolution});
    my $qcesm_tag   = $dbh->quote($item{cesm_tag});
    my $qcomments   = $dbh->quote($item{comments});
    my $qmachine    = $dbh->quote($item{machine});
    my $qrundate    = $dbh->quote($item{rundate});
    my $timing_file = $dbh->quote("../timing_files/" . $req->param('file'));

    my $sql = qq(INSERT INTO t_timeMaster (machine, resolution, compset, total_pes, cost, 
                       throughput, file_date, cesm_tag, comments, user_id, timing_file) 
                VALUES ($qmachine, $qresolution, $qcompset, $item{total_pes}, 
                        $item{model_cost}, $item{throughput}, $qrundate, $qcesm_tag, $qcomments, $item{luser_id}, $timing_file););
    my $sth = $dbh->prepare($sql);
    $sth->execute();
    $sth->finish;
    $item{t_timeMaster} = $sql;

    $sql = qq(SELECT LAST_INSERT_ID(););
    $sth = $dbh->prepare($sql);
    $sth->execute();
    $master_id = $sth->fetchrow();
    $sth->finish;

    #
    # Save Component Information to a component array
    #
    for my $i ( 0..$#componentarray)
    {
      #
      # Preping values for SQL insertion
      #
      my $qmodel    = $dbh->quote($componentarray[$i]->{model});
      my $qcomp_pe    = $dbh->quote($componentarray[$i]->{comp_pe});
      my $qroot_pe    = $dbh->quote($componentarray[$i]->{root_pe});
      my $qtasksXthreads = $dbh->quote("$componentarray[$i]->{tasks} X $componentarray[$i]->{threads}");

      $sql = qq(INSERT INTO t_timeComponent (name) VALUES ($qmodel););
      $sth = $dbh->prepare($sql);
      $sth->execute();
      $sth->finish;

      $sql = qq(SELECT LAST_INSERT_ID(););
      $sth = $dbh->prepare($sql);
      $sth->execute();
      $comp_id = $sth->fetchrow();
      $sth->finish;

      $sql = qq(INSERT INTO tj_time (comp_id, master_id, comp_pes, root_pes, tasks_threads) VALUES ($comp_id, $master_id, $qcomp_pe, $qroot_pe, $qtasksXthreads););
      $sth = $dbh->prepare($sql);
      $sth->execute();
      $sth->finish;
    }

    #
    # Sends the user to the updated timing submission form.
    #
    &successPage;
}

#----------------------------
# uploadAndParse 
#
# Uploads and Parses through
# the provided timing file
#----------------------------

sub uploadAndParse
{
    #
    # Set upload Directory and retrieve file info
    #
    my $uploadDir = "/home/www/html/timing/timing_files";    
    my $filename = $req->param('file');
    my $upload_filehandle = $req->upload('file');
    my $line;

    #
    # Save file to upload directory
    #
    open (UPLOADFILE, ">$uploadDir/$filename") or die "$!";
    binmode UPLOADFILE;
    while (<$upload_filehandle>)
    {
      print UPLOADFILE;
    }
    close UPLOADFILE;

    #
    # Begin Parsing of file
    #
    open my $file, '<', "$uploadDir/$filename";
    $line = <$file>;

    #
    # Check to see if file is actually a Timing File by checking first line in document.
    #
    if ($line !~ m/---------------- TIMING PROFILE ---------------------/)
    { 
      close ($file);
      &failurePage;
    }

    #
    # Parse the uploaded Timing file and Store the necessary information into the %item hash
    #
    while ($line = <$file>) 
    {
      ## Get User name
      #if ($line =~ m/^  User/)
      #{
      #  $line =~ /([a-zA-Z0-9]*)$/;
      #  $item{user_id} = $1;
      #}
      # Get Machine name
      #elsif ($line =~ m/^  Machine/)
      if ($line =~ m/^  Machine/)
      {
        $line =~ /([a-zA-Z0-9]*)$/;
        $item{machine} = $1;
      }
      # Get Run Date name
      elsif ($line =~ m/^  Curr Date/)
      {
        $line =~ /([a-zA-Z]*) (\d\d) (\d\d:\d\d:\d\d) ([a-zA_Z0-9]*)/;
	my $month = $mon2num{"$1"};
        $item{rundate} = "$4-$month-$2 $3";
      }
      # Get Total # of Active PEs
      elsif ($line =~ m/^  total pes active/)
      {
        $line =~ /(\d+)/;
        $item{total_pes} = $1;
      }
      # Get Model Cost
      elsif ($line =~ m/^    Model Cost/)
      {
        $line =~ /([0-9.]*)\s*pe-hrs\/simulated_year/;
        $item{model_cost} = $1;
      }
      # Get Model Throughput
      elsif ($line =~ m/^    Model Throughput/)
      {
        $line =~ /([0-9.]*)\s*simulated_years\/day/;
        $item{throughput} = $1;
      }

      # Get Component Information (Sorry for the crazy regexes)
      elsif ($line =~ m/^  component/)
      {
        $line = <$file>; 
        $line = <$file>;
        
        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %cpl = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
        $line = <$file>;

        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %atm = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
        $line = <$file>;

        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %lnd = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
	$line = <$file>;

        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %ice = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
        $line = <$file>;

        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %ocn = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
        $line = <$file>;

        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %rof = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
        $line = <$file>;

        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %glc = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
        $line = <$file>;

        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %wav = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
        $line = <$file>;

        $line =~ /([a-zA-Z]*)\s+=\s+([a-zA-Z0-9]*)\s+([0-9]*)\s+([0-9]*)\s+([0-9]*)\s*x\s*([0-9]*)\s+([0-9]*)\s+\(([0-9]*)\s+\)/;
        %esp = ( "component" => "$1", "model" => "$2", "comp_pe" => "$3", "root_pe" => "$4", "tasks" => "$5", "threads" => "$6", "instances" => "$7", "stride" => "$8");
      }
    }
    close ($file);

}

#-----------------------------------
# Success Page
#
# Directs the user to the updated
# form upon a successful submission
#-----------------------------------

sub successPage
{
    print header;
    print "<META HTTP-EQUIV=\"Refresh\" content =\"0; url=timings.cgi?a=s\">\n";
    exit 0;
}

#-------------------------------------
# Failure Page
#
# Returns user to submission form
# upon a failed submission, including
# an appropriate error message
#-------------------------------------

sub failurePage
{   

     my $vars = {
    	'cgi'=>$req, 
	'error'=>'failure',
	'cgiTag' => $req->param('cesm_tag'),
	'cgiAli' => $req->param('compset'),
	'cgiCom' => $req->param('comments'), 
	'cgiRes' => $req->param('resolution')
    };

    $dbh->disconnect;

    print header;
    my $tt_template = 'form.tt';   
    my $template = Template->new({ABSOLUTE => 1,EVAL_PERL => 1,INCLUDE_PATH => '/home/www/html/timing/templates'});
    $template->process($tt_template, $vars) || die ("Problem processing $tt_template, ", $template->error());

    exit 0;
}

exit 0;
