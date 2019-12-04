#!/usr/bin/env perl
#
# ASB - 2/14/2012 - login/logout logic from Jay S.
#
use warnings;
use strict;
use CGI;
use CGI::Carp qw(fatalsToBrowser);
use CGI::Session qw/-ip-match/;
use Template;
use Data::Dumper;
use Log::Log4perl;
use Exporter;
use lib qw(.);
use lib "/home/www/html/csegdb/lib";
use anon_auth;
use config;
use session;
use user;

my $req = CGI->new;

# get the username, password, action, and loginType.  
my $user = $req->param('username') unless ! defined $req->param('username');
my $password = $req->param('password') unless ! defined $req->param('password');
my $firstName = $req->param('firstName') unless ! defined $req->param('firstName');
my $lastName = $req->param('lastName') unless ! defined $req->param('lastName');
my $email_address = $req->param('email') unless ! defined $req->param('email');

my $action;
if (defined $req->param('action'))
{
    $action = $req->param('action');
}
else
{
    $action = '';
}
my $loginType = $req->param('loginType');

# get the session id if exists.  
my $sessionid = $req->param('CGISESSID');

# Check to see if the user has a valid session. This creates a session that needs to destroyed if there is an error.
my ($loggedin, $session) = &checksessionlogin($sessionid);
my ($anonloggedin) = &checkanonsessionlogin($sessionid);

#-----------------------------------------------------------------------------
# Main...
#-----------------------------------------------------------------------------

# If the action is 'logout', then do the logout. If the action is login, then login. 
# If the session is still logged in, redirect to the main page.  
# Otherwise, show the login page. 
if ($action eq 'logout')
{
	&logout($session);
}
elsif($action eq 'login')
{
	&login($session);
}
elsif($loggedin || $anonloggedin)
{
        &loginsuccess($req, $session);
}
else
{
	&showloginpage($req, undef, $session);
}

#-------------------------------------------------------------------------------------
# End main
#-------------------------------------------------------------------------------------


# Handle the login.  Call authenticate from the session library or manually. 
# If successful, make a new session, and redirect them to the main page. 
# otherwise, show them the login page again, with the login error included.  
sub login
{
    my ($session) = @_;
    my ($authsuccessful, $autherror);

    if ($loginType eq 'SVN') 
    {
	($authsuccessful, $autherror) = &svn_authenticate($user, $password);
    }
#    elsif($loginType eq 'UCAS')
#    {
#	($authsuccessful, $autherror) = &ucas_authenticate($user, $password);
#    }
    elsif($loginType eq 'CIT')
    {
        ($authsuccessful, $autherror) = &cit_authenticate($user, $password);
    }
    elsif($loginType eq 'OTHER')
    {
        ($authsuccessful, $autherror) = &anon_authenticate($firstName, $lastName, $email_address);
    }

    if($authsuccessful == 1)
    {
	$session = &getuserbyusername($user, $session);
	$session = &makeloginsession($req, $user, $session);
	&loginsuccess($req, $session);
    }
    elsif($authsuccessful == 2)
    {
        $session = &makeanonloginsession($req, $firstName, $lastName, $email_address, $session);
        &loginsuccess($req, $session);
    }
    else
    {
	&showloginpage($req, $autherror, $session );
    }

}

# Logout.  Logout the session, delete everything from the req, and show the login page. 
sub logout
{
	my ($session) = @_;
	&sessionlogout($session);
	$req->delete();
	&showloginpage($req, undef);
}

# Show the login page template.  If there is an error message, show that too. 
sub showloginpage
{
	my ($req, $error) = @_;
	
	my $vars = {
                'cgi' => $req,
		'error' => $error,
	};

	#my $loginpage = "../templates/login.tt";
	#my $tt_template = "login.tmpl";
	my $tt_template = "login.tt";
	my $tt = Template->new(INCLUDE_PATH => "/home/www/html/timing/templates", ABSOLUTE => 1, EVAL_PERL => 1);
	print "Content-type: text/html \n\n";
	$tt->process($tt_template, $vars) or die ("problem processing $tt_template,", $tt->error());
}

# Either the session is still valid, or someone just logged in.  Set the 
# cookie on the cgi request, then redirect to expList.cgi. 
sub loginsuccess
{
    my ($req, $session) = @_;
    
    my $cookie = $req->cookie(CGISESSID => $session->id);
    print $req->header(-cookie => $cookie);

    print "<html>\n";
    print "<head>\n";
    print "<META HTTP-EQUIV=\"Refresh\" content =\"0; url=upload.cgi\">\n";
    print "</head>\n";
    print "</html>";
}

