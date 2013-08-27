from distutils.core import setup
import glob,re, os



def get_version():
  """
  Gets version from osg-configure script file
  """
  buffer = open('scripts/skeleton_key').read()
  match = re.search("VERSION\s+=\s+'(.*)'", buffer)
  return match.group(1)
  
setup(name='skeletonkey',
      version=get_version(),
      description='Package for skeleton-key and associated scripts',
      author='Suchandra Thapa',
      author_email='sthapa@ci.uchicago.edu',
      url='http://sk.uchicago.edu',
      scripts=['scripts/skeleton_key'],
      data_files=[('share/skeletonkey', ['scripts/run_job.py'])]
      )

