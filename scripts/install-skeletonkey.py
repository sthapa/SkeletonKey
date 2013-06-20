#!/usr/bin/python

import os, optparse, sys, re, urllib2, tarfile, tempfile, shutil, platform

version = '0.7'

def setup_chirp(options, cctools_dir):
    """Setup .chirp and setup chirp options"""
    chirp_dir = os.path.expanduser('~/.chirp')
    if not os.path.exists(chirp_dir):
        os.mkdir(chirp_dir, 0700)
    chirp_config_path = os.path.join(chirp_dir, "chirp_options")
    chirp_config = open(chirp_config_path, "w")
    if options.hdfs_uri is not None:
        chirp_config.write("HDFS_URI=\"%s\"\n" % options.hdfs_uri)
    elif options.export_dir is not None:
        chirp_config.write("EXPORT_DIR=\"%s\"\n" % options.export_dir)
    else:
        sys.stderr.write("Export directory for chirp not given!\n")
        sys.exit(1)
    chirp_config.write("CCTOOLS_BINDIR=%s\n" % cctools_dir)
    chirp_config.write("CHIRP_HOST=%s\n" % os.uname()[1])
    chirp_config.close()

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

def setup_cctools_binaries(options):
    """Download the appropriate version of cctools and install"""
    for os_version in ('5', '6'):
      cctools_url = "http://www3.nd.edu/~ccl/software/files/" \
                    "cctools-current-x86_64-redhat%s.tar.gz" % (os_version)
      cctools_dir = download_tarball(cctools_url, options.bin_dir)
      if os_version == platform.dist()[1][0]: 
        os.link(os.path.join(cctools_dir, 'bin', 'chirp_server'),
                os.path.join(options.bin_dir, 'chirp_server'))
        os.link(os.path.join(cctools_dir, 'bin', 'chirp_server_hdfs'),
                os.path.join(options.bin_dir, 'chirp_server_hdfs'))
        os.link(os.path.join(cctools_dir, 'bin', 'chirp'),
                os.path.join(options.bin_dir, 'chirp'))
        sys_cctools_dir = cctools_dir
      shutil.copytree(cctools_dir, os.path.join(options.bin_dir, 'parrot'))
      current_dir = os.getcwd()
      os.chdir(options.bin_dir)
      shutil.rmtree(os.path.join('parrot', 'doc'))
      shutil.rmtree(os.path.join('parrot', 'share'))
      tarball = tarfile.open("parrot-sl%s.tar.gz" % os_version, mode='w:gz')
      tarball.add('parrot')
      tarball.close()
      shutil.rmtree('parrot')
      if os_version != platform.dist()[1][0]:
        shutil.rmtree(cctools_dir)
      os.chdir(current_dir)

    return os.path.abspath(sys_cctools_dir)

def setup_sk_binaries(options):
    """Download the appropriate version of SkeletonKey and install"""

    sk_url = "http://uc3-data.uchicago.edu/sk/skeleton-key-current.tar.gz"   
    sk_dir = download_tarball(sk_url, options.bin_dir)
    os.link(os.path.join(sk_dir, 'scripts', 'skeleton_key'),
            os.path.join(options.bin_dir, 'skeleton_key'))
    os.link(os.path.join(sk_dir, 'scripts', 'chirp_control'),
            os.path.join(options.bin_dir, 'chirp_control'))
    return os.path.abspath(sk_dir)


def install_application():
    """Get responses and install skeletonKey based on user responses"""
    parser = optparse.OptionParser(version="%prog " + version)
    parser.add_option("-b", "--bindir", dest="bin_dir",
                      help="Directory to install binaries in", 
                      metavar="BINDIR")
    parser.add_option("-e", "--exportdir", dest="export_dir",
                      help="Directory to export in CHIRP, exclusive with -h",
                      metavar="EXPORTDIR")
    parser.add_option("-u", "--hdfs-uri", dest="hdfs_uri",
                      help="URI of HDFS directory to export, exclusive with -e",
                      metavar="HDFS_URI")
    (options, args) = parser.parse_args()
    
    if (options.hdfs_uri is not None and  options.export_dir is not None):
      parser.error("Can't specify both -e and -u, please choose one\n")
    if (options.bin_dir is None):
      parser.error("Please give the directory to install the " +
                   "SkeletonKey binaries in\n")
    if ((options.export_dir is None and options.hdfs_uri is None)):
      parser.error("Please give specify whether a local directory or " +
                   "HDFS uri to export")
    if (not os.path.exists(options.bin_dir) or 
        not os.path.isdir(options.bin_dir)):
      parser.error("Binary direction not present: %s" % options.bin_dir)
      
    cctools_dir = setup_cctools_binaries(options)
    sk_dir = setup_sk_binaries(options)
    setup_chirp(options, cctools_dir)
    setup_skeletonkey(options, sk_dir)
    install_location = os.path.abspath(options.bin_dir)
    sys.stdout.write("SkeletonKey and CCTools installed in %s\n" % install_location)
    sys.stdout.write("Chirp configuration saved to ~/.chirp\n")
    sys.stdout.write("SkeletonKey configuration saved to ~/.skeletonkey.config\n")

if __name__ == '__main__':
    install_application()
    sys.exit(0)
