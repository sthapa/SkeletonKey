#!/usr/bin/python

import sys, os, subprocess, shutil, optparse, platform, tempfile, urllib2, tarfile

TICKET_CONTENTS = """%%%TICKET%%%
"""
CHIRP_MOUNT = '%%%CHIRP_MOUNT%%%'
WEB_PROXY= '%%%WEB_PROXY%%%'
APP_URL = '%%%APP_URL%%%'
PARROT_URL = '%%%PARROT_URL%%%'
JOB_SCRIPT = '%%%JOB_SCRIPT%%%'
JOB_ARGS = %%%JOB_ARGS%%%
CVMFS_INFO = %%%CVMFS_INFO%%%
version = '0.5'

def write_ticket(directory):
  """
  Write out ticket information in directory specified
  """
  if not os.path.exists(directory) or not os.path.isdir(directory):
    return None
  try:
    ticket = open(os.path.join(directory, 'chirp.ticket'), 'w')
    ticket.write(TICKET_CONTENTS)
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
  extract_path = os.path.join(path,
                              downloaded_tarfile.getmembers()[0].name)
  downloaded_tarfile.extractall(path=path)
  os.unlink(download_file)
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
  job_env['PARROT_ALLOW_SWITCHING_CVMFS_REPOSITORIES'] = '1'
  job_env['PARROT_HELPER'] = os.path.join(parrot_path,
                                          'lib',
                                          'libparrot_helper.so')
  job_env['CHIRP_MOUNT'] = CHIRP_MOUNT
  return job_env 

def run_application(temp_dir):
  """
  Run specified user application in a parrot environment
  """
  job_env = generate_env(temp_dir)
  job_args = [JOB_SCRIPT]
  job_args.extend(JOB_ARGS.split(' '))
  if len(sys.argv) > 1:
    job_args.extend(sys.argv[1:])

  process_obj = subprocess.Popen(job_args, 
                                 env=job_env)
  process_obj.communicate()

def main():
  """Setup and run application"""
  parser = optparse.OptionParser(version="%prog " + version)
  parser.add_option("-d", "--debug", 
                    dest="debug",
                    help="Enabling debugging",
                    action="store_true", 
                    default=False)
  (options, args) = parser.parse_args()  
  try:
    temp_dir = tempfile.mkdtemp()
  except IOError:
    sys.stderr.write("Can't create temporary directory, exiting...\n")
    sys.exit(1)


  if TICKET_CONTENTS != "":
#    if ticket_expired(TICKET_CONTENTS):
#      sys.stderr.write("ERROR: Ticket expired, exiting...\n")
#      sys.exit(1)
    if not write_ticket(temp_dir):
      sys.stderr.write("Can't create ticket, exiting...\n")
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
    sys.exit(exit_code)
  if not options.debug:
    shutil.rmtree(temp_dir)
  sys.exit(exit_code)

if __name__ == '__main__':
  main()
