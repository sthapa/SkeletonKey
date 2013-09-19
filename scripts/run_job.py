#!/usr/bin/python

#  File:     run_job.py
#
#  Author:   Suchandra Thapa
#  e-mail:   sthapa@ci.uchicago.edu
#
#
# Copyright (c) University of Chicago. 2013
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, subprocess, shutil, optparse, platform, tempfile, urllib2
import tarfile, urlparse, time, re

TICKET_CONTENTS = """%%%TICKET%%%
"""
OSGC_PROXY = 'http://squid.osgconnect.net:3128'
CATALOG_HOST = 'stash.opensciencegrid.net'
CHIRP_MOUNT = '%%%CHIRP_MOUNT%%%'
WEB_PROXY= '%%%WEB_PROXY%%%'
USER_PROXY = """%%%USER_PROXY%%%"""
APP_URL = '%%%APP_URL%%%'
PARROT_URL = '%%%PARROT_URL%%%'
JOB_SCRIPT = '%%%JOB_SCRIPT%%%'
JOB_ARGS = %%%JOB_ARGS%%%
CVMFS_INFO = %%%CVMFS_INFO%%%
VERSION = '0.11-osgc'

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

def ticket_valid(): 
  """
  Check a ticket to see if it's still valid
  """
  if TICKET_CONTENTS == "":
    # Don't need to worry about ticket expiration if the ticket is not present
    return True
  ticket_expiration = re.compile(r'Expires on (\w+\s+\w+\s+\d{1,2}\s+\d\d:\d\d:\d\d\s+\d{4})')
  match = ticket_expiration.search(TICKET_CONTENTS)
  if match is None:
    # if no expiration written, assume ticket doesn't expire
    return True
  expiration = time.strptime(match.group(1),
                             "%a %b %d %H:%M:%S %Y")
  return time.time() > time.mktime(expiration)

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
  else:
    job_env['http_proxy'] = OSGC_PROXY
    job_env['HTTP_PROXY'] = OSGC_PROXY
    
  if job_env.has_key('OSG_SQUID_LOCATION') and job_env['OSG_SQUID_LOCATION'] != 'UNAVAILABLE':
    job_env['http_proxy'] = job_env['OSG_SQUID_LOCATION']
    job_env['HTTP_PROXY'] = job_env['OSG_SQUID_LOCATION']
  
  job_env['PARROT_ALLOW_SWITCHING_CVMFS_REPOSITORIES'] = '1'
  job_env['PARROT_HELPER'] = os.path.join(parrot_path,
                                          'parrot',
                                          'lib',
                                          'libparrot_helper.so')
  job_env['CHIRP_MOUNT'] = CHIRP_MOUNT
  job_env['CATALOG_HOST'] = CATALOG_HOST
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
#    if os.path.isdir(os.path.join('/', 'cvmfs', k)):
#      continue
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
  if TICKET_CONTENTS != "":
    job_args.extend(['-i', 'chirp.ticket'])
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


  if TICKET_CONTENTS != "":
    if not ticket_valid():
      sys.stderr.write("ERROR: Ticket expired, exiting...\n")
      sys.exit(1)
    if not write_ticket(temp_dir):
      sys.stderr.write("Can't create ticket, exiting...\n")
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
