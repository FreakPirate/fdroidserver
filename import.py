#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# import.py - part of the FDroid server tools
# Copyright (C) 2010-12, Ciaran Gultnieks, ciaran@ciarang.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import shutil
import subprocess
import re
import urllib
from optparse import OptionParser

#Read configuration...
repo_name = None
repo_description = None
repo_icon = None
repo_url = None
execfile('config.py')

import common

# Parse command line...
parser = OptionParser()
parser.add_option("-u", "--url", default=None,
                  help="Project URL to import from.")
parser.add_option("-s", "--subdir", default=None,
                  help="Path to main android project subdirectory, if not in root.")
(options, args) = parser.parse_args()

if not options.url:
    print "Specify project url."
    sys.exit(1)
url = options.url

tmp_dir = 'tmp'
if not os.path.isdir(tmp_dir):
    print "Creating temporary directory"
    os.makedirs(tmp_dir)

# Get all apps...
apps = common.read_metadata()

# Figure out what kind of project it is...
projecttype = None
if url.startswith('https://github.com'):
    projecttype = 'github'
    repo = url + '.git'
    repotype = 'git'
    sourcecode = url
elif url.startswith('http://code.google.com/p/'):
    if not url.endswith('/'):
        print "Expected format for googlecode url is http://code.google.com/p/PROJECT/"
        sys.exit(1)
    projecttype = 'googlecode'
    sourcecode = url + 'source/checkout'
    req = urllib.urlopen(sourcecode)
    if req.getcode() != 200:
        print 'Unable to find source at ' + sourcecode + ' - return code ' + str(req.getcode())
        sys.exit(1)
    page = req.read()
    repotype = None
    index = page.find('hg clone')
    if index != -1:
        repotype = 'hg'
        repo = page[index + 9:]
        index = repo.find('<')
        if index == -1:
            print "Error while getting repo address"
            sys.exit(1)
        repo = repo[:index]
    if not repotype:
        index=page.find('git clone')
        if index != -1:
            repotype = 'git'
            repo = page[index + 10:]
            index = repo.find('<')
            if index == -1:
                print "Error while getting repo address"
                sys.exit(1)
            repo = repo[:index]
    if not repotype:
        print "Unable to determine vcs type"
        sys.exit(1)

if not projecttype:
    print "Unable to determine the project type."
    sys.exit(1)

# Get a copy of the source so we can extract some info...
print 'Getting source from ' + repotype + ' repo at ' + repo
src_dir = os.path.join(tmp_dir, 'importer')
if os.path.exists(tmp_dir):
    shutil.rmtree(tmp_dir)
vcs = common.getvcs(repotype, repo, src_dir)
vcs.gotorevision(None)
if options.subdir:
    root_dir = os.path.join(src_dir, options.subdir)
else:
    root_dir = src_dir

# Check AndroidManiifest.xml exists...
manifest = os.path.join(root_dir, 'AndroidManifest.xml')
if not os.path.exists(manifest):
    print "AndroidManifest.xml did not exist in the expected location. Specify --subdir?"
    sys.exit(1)

# Extract some information...
vcsearch = re.compile(r'.*android:versionCode="([^"]+)".*').search
vnsearch = re.compile(r'.*android:versionName="([^"]+)".*').search
psearch = re.compile(r'.*package="([^"]+)".*').search
version = None
vercode = None
package = None
for line in file(manifest):
    if not package:
        matches = psearch(line)
        if matches:
            package = matches.group(1)
    if not version:
        matches = vnsearch(line)
        if matches:
            version = matches.group(1)
    if not vercode:
        matches = vcsearch(line)
        if matches:
            vercode = matches.group(1)
if not package:
    print "Couldn't find package ID"
    sys.exit(1)
if not version:
    print "Couldn't find latest version name"
    sys.exit(1)
if not vercode:
    print "Couldn't find latest version code"
    sys.exit(1)

# Make sure it's actually new...
for app in apps:
    if app['id'] == package:
        print "Package " + package + " already exists"
        sys.exit(1)

# Construct the metadata...
app = common.parse_metadata(None)
app['id'] = package
app['Web Site'] = url
app['Source Code'] = sourcecode
app['Repo Type'] = repotype
app['Repo'] = repo

# Create a build line...
build = {}
build['version'] = version
build['vercode'] = vercode
build['commit'] = '?'
if options.subdir:
    build['subdir'] = options.subdir
if os.path.exists(os.path.join(root_dir, 'jni')):
    build['buildjni'] = 'yes'
app['builds'].append(build)
app['comments'].append(('build:' + version,
    "#Generated by import.py - check this is the right version, and find the right commit!"))

metafile = os.path.join('metadata', package + '.txt')
common.write_metadata(metafile, app)
print "Wrote " + metafile
