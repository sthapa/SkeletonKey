#!/usr/bin/python

import os, optparse, sys, re, urllib2, tarfile, tempfile

version = '1.0'

def setup_chirp(options, cctools_dir):
    """Setup .chirp and setup chirp options"""
    chirp_dir = os.path.expanduser('~/.chirp')
    if not os.path.exists(chirp_dir):
        os.mkdir(chirp_dir, 0700)
    chirp_config_path = os.path.join(chirp_dir, "chirp_options")
    chirp_config = open(chirp_config_path, "w")
    if options.hdfs_uri is not None:
        chirp_config.write("HDFS_URI=\"%s\"\n" % hdfs_uri)
    elif options.export_dir is not None:
        chirp_config.write("EXPORT_DIR=\"%s\"\n" % options.export_dir)
    else:
        sys.stderr.write("Export directory for chirp not given!\n")
        sys.exit(1)
    chirp_config.wrote("CCTOOLS_BINDIR=%\n" % cctools_dir)
    chirp_config.close()

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

def setup_binaries(options):
    """Download the appropriate version of cctools and install"""
    release_info = open('/etc/redhat-release').read()
    match = re.search('release\s(\d)', release_info)
    if match is None:
        sys.stderr.write("Can't get RHEL/SL version on this system\n")
        sys.exit(1)
    else:
       os_version = match.group(1)
    cctools_page = urllib2.urlopen('http://www3.nd.edu/~ccl/software/files/').read()
    latest_version = None
    try:
        latest_version  = re.findall('href=cctools-(\d\.\d\.\d)-source.tar.gz', 
                                     cctools_page)[-1]
    except:
        sys.stderr.write("Can't get cctools tarball link\n")
        sys.exit(1)
    cctools_url = "http://www3.nd.edu/~ccl/software/files/" \
                  "cctools-%s-x86_64-redhat%s.tar.gz" % (latest_version, 
                                                         os_version)
    cctools_dir = download_tarball(cctools_url, options.bin_dir)
    os.link(os.path.join(cctools_dir, 'bin', 'chirp_server'),
            os.path.join(options.bin_dir, 'chirp_server'))
    os.link(os.path.join(cctools_dir, 'bin', 'chirp_server_hdfs'),
            os.path.join(options.bin_dir, 'chirp_server_hdfs'))

    sk_url = "http://uc3-data.uchicago.edu/skeletonkey/skeletonkey-current.tar.gz"   
    sk_dir = download_tarball(sk_url, options.bin_dir)
    os.link(os.path.join(sk_dir, 'bin', 'skeleton_key'),
            os.path.join(options.bin_dir, 'skeleton_key'))
    os.link(os.path.join(sk_dir, 'bin', 'chirp_control'),
            os.path.join(options.bin_dir, 'chirp_control'))
    return cctools_dir


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
    cctools_dir = setup_binaries(options)
    setup_chirp(options, cctools_dir)

if __name__ == '__main__':
    install_application()
    sys.exit(0)
