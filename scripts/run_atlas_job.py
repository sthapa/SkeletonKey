#!/usr/bin/python

import sys, os, subprocess, shutil, optparse, platform, tempfile, urllib2, tarfile
import urlparse, time, re

WEB_PROXY= 'uc3-data.uchicago.edu:3128'
USER_PROXY = """%%%USER_PROXY%%%"""
APP_URL = '%%%APP_URL%%%'
PARROT_URL = 'http://uc3-data.uchicago.edu/parrot/'
JOB_SCRIPT = '%%%JOB_SCRIPT%%%'
JOB_ARGS = %%%JOB_ARGS%%%
CVMFS_INFO = {'atlas.cern.ch': {'options': 'url=http://cvmfs.racf.bnl.gov:8000/opt/atlas;http://cvmfs-stratum-one.cern.ch:8000/opt/atlas,pubkey=cern.ch.pub,quota_limit=2000,proxies=uc3-data.uchicago.edu:3128', 'key': 'http://uc3-data.uchicago.edu/keys/cern.ch.pub'}, 'oasis.opensciencegrid.org': {'options': 'url=http://oasis-replica.opensciencegrid.org:8000/cvmfs/oasis;http://cvmfs.fnal.gov:8000/cvmfs/oasis;http://cvmfs.racf.bnl.gov:8000/cvmfs/oasis,pubkey=opensciencegrid.org.pub,quota_limit=2000,proxies=uc3-data.uchicago.edu:3128', 'key': 'http://uc3-data.uchicago.edu/keys/opensciencegrid.org.pub'}, 'atlas-condb.cern.ch': {'options': 'url=http://cvmfs.racf.bnl.gov:8000/opt/atlas-condb;http://cvmfs-stratum-one.cern.ch:8000/opt/atlas-condb,pubkey=cern.ch.pub,quota_limit=2000,proxies=uc3-data.uchicago.edu:3128', 'key': 'http://uc3-data.uchicago.edu/keys/cern.ch.pub'}, 'osg.mwt2.org': {'options': 'url=http://uct2-cvmfs.mwt2.org/opt/osg,pubkey=mwt2.org.pub,quota_limit=2000,proxies=uc3-data.uchicago.edu:3128', 'key': 'http://uc3-data.uchicago.edu/keys/mwt2.org.pub'}}
VERSION = '0.10'

def write_proxy(directory):
  """
  Extract and create user proxy file for application
  """
  if not os.path.exists(directory) or not os.path.isdir(directory):
    return None
  try:
    ticket = open(os.path.join(directory, 'user_proxy'), 'w')
    ticket.write(USER_PROXY)
    ticket.close()
    return True
  except IOError:
    return None

def download_tarball(url, path):
  """Download a tarball from a given url and extract it to specified path"""

  (fhandle, download_file) = tempfile.mkstemp(dir=path)
  url_handle = urllib2.urlopen(url)
  url_data = url_handle.read(2048)
  while url_data:
    os.write(fhandle, url_data)
    url_data = url_handle.read(2048)
  os.close(fhandle)
  downloaded_tarfile = tarfile.open(download_file)
  cur_dir = os.getcwd()
  os.chdir(path)
  extract_path = os.path.join(path,
                              downloaded_tarfile.getmembers()[0].name)
  for tar_info in downloaded_tarfile:
    downloaded_tarfile.extract(tar_info)
  os.unlink(download_file)
  os.chdir(cur_dir)
  return extract_path

def setup_application(directory):
  """
  Download application binaries and setup in temp directory
  """
  app_path = download_tarball(APP_URL, directory)
  return app_path

def setup_parrot(directory):
  """
  Download correct parrot binaries and setup in temp directory
  """
  sys_ver = platform.dist()[1][0]
  parrot_url = PARROT_URL + "/parrot-sl%s.tar.gz" % sys_ver
  parrot_path = download_tarball(parrot_url, directory)
  return parrot_path

def generate_env(parrot_path):
  """
  Create a dict with the environment variables for binary + parrot
  """
  job_env = os.environ.copy()
    
  if WEB_PROXY != "":
    job_env['http_proxy'] = WEB_PROXY
    job_env['HTTP_PROXY'] = WEB_PROXY
  if job_env.has_key('OSG_SQUID_LOCATION') and job_env['OSG_SQUID_LOCATION'] != 'UNAVAILABLE':
    job_env['http_proxy'] = job_env['OSG_SQUID_LOCATION']
    job_env['HTTP_PROXY'] = job_env['OSG_SQUID_LOCATION']
  job_env['PARROT_ALLOW_SWITCHING_CVMFS_REPOSITORIES'] = '1'
  job_env['PARROT_HELPER'] = os.path.join(parrot_path,
                                          'parrot',
                                          'lib',
                                          'libparrot_helper.so')
  return job_env 

def update_proxy(cvmfs_options):
  """
  Update cvmfs options to use local proxy if available
  """
  new_proxies = ""
  if WEB_PROXY != "":   
    new_proxies = WEB_PROXY + ";"
  if os.environ.has_key('OSG_SQUID_LOCATION') and os.environ['OSG_SQUID_LOCATION'] != 'UNAVAILABLE':
    new_proxies += "%s;" % os.environ['OSG_SQUID_LOCATION']
  proxy_re = re.compile(r'proxies=(.*?)(,|$)')
  return proxy_re.sub(r'proxies=' + new_proxies + r'\1\2', cvmfs_options)

def create_cvmfs_options():
  """
  Create  CVMFS options for parrot
  """
  if len(CVMFS_INFO) == 0:
    return ' '
  cvmfs_opts = ''
  for k in CVMFS_INFO:
    cvmfs_options = update_proxy(CVMFS_INFO[k]['options'])
    cvmfs_opts += "%s:%s " % (k, cvmfs_options)
  return cvmfs_opts[:-1]

def get_cvmfs_keys(temp_dir):
  """
  Download cvmfs keys for repositories that have been defined
  """
  for k in CVMFS_INFO:
    key_url = CVMFS_INFO[k]['key']
    url_handle = urllib2.urlopen(key_url)
    key_name = urlparse.urlparse(key_url)[2].split('/')[-1]
    key_file = open(os.path.join(temp_dir, key_name), 'w')
    url_data = url_handle.read(2048)
    while url_data:
      key_file.write(url_data)
      url_data = url_handle.read(2048)
    key_file.close()

def run_application(temp_dir):
  """
  Run specified user application in a parrot environment
  """
  job_env = generate_env(temp_dir)
  get_cvmfs_keys(temp_dir)
  job_args = ['./parrot/bin/parrot_run', 
              '-t',
              os.path.join(temp_dir, 'parrot_cache'),
              '-r',
              create_cvmfs_options()]
  job_args.append(JOB_SCRIPT)
  if JOB_ARGS != "":
    job_args.extend(JOB_ARGS.split(' '))
  os.chdir(temp_dir)
  if len(sys.argv) > 1:
    job_args.extend(sys.argv[1:])

  return subprocess.call(job_args, env=job_env)

def main():
  """Setup and run application"""
  parser = optparse.OptionParser(version="%prog " + VERSION)
  parser.add_option("-d", "--debug", 
                    dest="debug",
                    help="Enabling debugging",
                    action="store_true", 
                    default=False)
  parser.add_option("--preserve-dir", 
                    dest="preserve_dir",
                    help="Preserver working directory for debugging",
                    action="store_true", 
                    default=False)
  (options, args) = parser.parse_args()  
  try:
    temp_dir = tempfile.mkdtemp()
  except IOError:
    sys.stderr.write("Can't create temporary directory, exiting...\n")
    sys.exit(1)


  if USER_PROXY != "":
    if not write_proxy(temp_dir):
      sys.stderr.write("Can't create user proxy, exiting...\n")
      sys.exit(1)
   
  if not setup_parrot(temp_dir):
    sys.stderr.write("Can't download parrot binaries, exiting...\n")
    sys.exit(1)
  if APP_URL != '':
    if not setup_application(temp_dir):       
      sys.stderr.write("Can't download application binaries, exiting...\n")
      sys.exit(1)
  exit_code = run_application(temp_dir)
  if exit_code != 0:
    sys.stderr.write("Application exited with error\n")
    if options.debug:
      sys.stderr.write("Exit code: %d\n" % exit_code)
    sys.exit(exit_code)
    
  if options.preserve_dir:
    sys.stdout.write("Temp directory at %s\n" % temp_dir)
  else:
    shutil.rmtree(temp_dir)
  sys.exit(exit_code)

if __name__ == '__main__':
  main()
