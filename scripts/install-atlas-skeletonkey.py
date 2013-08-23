#!/usr/bin/python

#  File:     install-atlas-skeletonkey.py
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

import os, optparse, sys, re, urllib2, tarfile, tempfile, shutil, platform

VERSION = '0.9'

def setup_skeletonkey(options, sk_dir):
    """Setup .skeletonkey and setup skeletonkey options"""
    sk_config_path = os.path.expanduser('~/.skeletonkey.config')
    sk_config = open(sk_config_path, "w")
    sk_config.write("[Installation]\n")
    sk_config.write("location = %s\n" % sk_dir)
    sk_config.close()

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

def setup_sk_binaries(options):
    """Download the appropriate version of SkeletonKey and install"""

    sk_url = "http://uc3-data.uchicago.edu/sk/atlas-skeleton-key-current.tar.gz"   
    sk_dir = download_tarball(sk_url, options.bin_dir)
    os.link(os.path.join(sk_dir, 'scripts', 'atlas_skeleton_key'),
            os.path.join(options.bin_dir, 'atlas_skeleton_key'))
    os.link(os.path.join(sk_dir, 'scripts', 'atlas_shell'),
            os.path.join(options.bin_dir, 'atlas_shell'))
    os.renames(os.path.join(sk_dir, 'scripts', 'run_atlas_job.py'),
              os.path.join(sk_dir, 'templates', 'run_atlas_job.py'))
    return os.path.abspath(sk_dir)


def install_application():
    """Get responses and install skeletonKey based on user responses"""
    parser = optparse.OptionParser(version="%prog " + VERSION)
    parser.add_option("-b", "--bindir", dest="bin_dir",
                      help="Directory to install binaries in", 
                      metavar="BINDIR")
    (options, args) = parser.parse_args()
    
    if (options.bin_dir is None):
      parser.error("Please give the directory to install the " +
                   "SkeletonKey binaries in\n")
    if (not os.path.exists(options.bin_dir) or 
        not os.path.isdir(options.bin_dir)):
      parser.error("Binary direction not present: %s" % options.bin_dir)
      
    sk_dir = setup_sk_binaries(options)
    setup_skeletonkey(options, sk_dir)
    install_location = os.path.abspath(options.bin_dir)
    sys.stdout.write("SkeletonKey for ATLAS installed in %s\n" % install_location)
    sys.stdout.write("SkeletonKey configuration saved to ~/.skeletonkey.config\n")

if __name__ == '__main__':
    install_application()
    sys.exit(0)
