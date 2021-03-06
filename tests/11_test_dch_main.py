# vim: set fileencoding=utf-8 :

"""Test L{gbp.scripts.dch} main"""

from . import context

import unittest

from tests.testutils import DebianGitTestRepo, OsReleaseFile

from gbp.scripts import dch

import os
import re

# For Ubuntu compatibility
os_release = OsReleaseFile('/etc/lsb-release')

# OS release codename and snapshot of version 0.9-2~1
if os_release['DISTRIB_ID'] == 'Ubuntu':
    os_codename = os_release['DISTRIB_CODENAME']
    snap_header_0_9 = r'^test-package\s\(0.9-1ubuntu1~1\.gbp([0-9a-f]{6})\)\sUNRELEASED;\surgency=low'
    new_version_0_9 = '0.9-1ubuntu1'
else:
    os_codename = 'unstable'
    snap_header_0_9 = r'^test-package\s\(0.9-2~1\.gbp([0-9a-f]{6})\)\sUNRELEASED;\surgency=low'
    new_version_0_9 = '0.9-2'
# Snapshot of version 1.0-1~1
snap_header_1 = r'^test-package\s\(1.0-1~1\.gbp([0-9a-f]{6})\)\sUNRELEASED;\surgency=low'
# Snapshot of version 1.0-1~2
snap_header_1_2 = r'^test-package\s\(1.0-1~2\.gbp([0-9a-f]{6})\)\sUNRELEASED;\surgency=low'

snap_mark = r'\s{2}\*{2}\sSNAPSHOT\sbuild\s@'

deb_tag = "debian/0.9-1"
deb_tag_msg = "Pre stable release version 0.9-1"

cl_debian = """test-package (0.9-1) unstable; urgency=low

  [ Debian Maintainer ]
  * New pre stable upstream release

 -- Debian Maintainer <maint@debian.org>  Mon, 17 Oct 2011 10:15:22 +0200
"""


@unittest.skipIf(not os.path.exists('/usr/bin/dch'), "Dch not found")
class TestScriptDch(DebianGitTestRepo):
    """Test git-dch"""


    def setUp(self):
        DebianGitTestRepo.setUp(self)
        self.add_file("foo", "bar")
        self.repo.create_tag("upstream/0.9", msg="upstream version 0.9")
        self.add_file("bar", "foo")
        self.repo.create_tag("upstream/1.0", msg="upstream version 1.0")
        self.repo.create_branch("debian")
        self.repo.set_branch("debian")
        self.upstream_tag = "upstream/%(version)s"
        self.top = os.path.abspath(os.path.curdir)
        os.mkdir(os.path.join(self.repo.path, "debian"))
        context.chdir(self.repo.path)
        self.add_file("debian/changelog", cl_debian)
        self.add_file("debian/control", """Source: test-package\nSection: test\n""")
        self.options = ["--upstream-tag=%s" % self.upstream_tag, "--debian-branch=debian",
                        "--id-length=0", "--spawn-editor=/bin/true"]
        self.repo.create_tag(deb_tag, msg=deb_tag_msg, commit="HEAD~1")


    def tearDown(self):
        DebianGitTestRepo.tearDown(self)


    def run_dch(self, dch_options=None):
        # Take care to copy the list
        options = self.options[:]
        if dch_options is not None:
            options.extend(dch_options)
        ret = dch.main(options)
        self.assertEqual(ret, 0)
        return file("debian/changelog").readlines()


    def test_dch_main_new_upstream_version(self):
        """Test dch.py like git-dch script does: new upstream version"""
        lines = self.run_dch()
        self.assertEqual("test-package (1.0-1) UNRELEASED; urgency=low\n", lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_release(self):
        """Test dch.py like git-dch script does: new upstream version - release"""
        options = ["--release"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (1.0-1) %s; urgency=low\n" % os_codename, lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_auto(self):
        """Test dch.py like git-dch script does: new upstream version - guess last commit"""
        options = ["--auto"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (1.0-1) UNRELEASED; urgency=low\n", lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_snapshot(self):
        """Test dch.py like git-dch script does: new upstream version - snapshot mode"""
        options = ["--snapshot"]
        lines = self.run_dch(options)
        header = re.search(snap_header_1, lines[0])
        self.assertIsNotNone(header)
        self.assertEqual(header.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_2_snapshots_auto(self):
        """Test dch.py like git-dch script does: new upstream version - two snapshots - auto"""
        options = ["--snapshot"]
        lines = self.run_dch(options)
        header1 = re.search(snap_header_1, lines[0])
        self.assertIsNotNone(header1)
        self.assertEqual(header1.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header1.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)
        # New snapshot, use auto to guess last one
        self.add_file("debian/compat", "9")
        options.append("--auto")
        lines = self.run_dch(options)
        header2 = re.search(snap_header_1_2, lines[0])
        self.assertIsNotNone(header2)
        self.assertEqual(header2.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header2.group(1), lines[2]))
        # First snapshot entry must be concatenated with the last one
        self.assertNotIn(header1.group(0) + "\n", lines)
        self.assertIn("""  * added debian/control\n""", lines)
        self.assertIn("""  * added debian/compat\n""", lines)


    def test_dch_main_new_upstream_version_with_2_snapshots_commit_auto(self):
        """Test dch.py like git-dch script does: new upstream version - two committed snapshots - auto"""
        options = ["--commit"]
        options.append("--commit-msg=TEST-COMMITTED-SNAPSHOT")
        options.append("--snapshot")
        lines = self.run_dch(options)
        header1 = re.search(snap_header_1, lines[0])
        self.assertIsNotNone(header1)
        self.assertEqual(header1.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header1.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)
        # New snapshot, use auto to guess last one
        self.add_file("debian/compat", "9")
        options.append("--auto")
        lines = self.run_dch(options)
        header2 = re.search(snap_header_1_2, lines[0])
        self.assertIsNotNone(header2)
        self.assertEqual(header2.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header2.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)
        self.assertIn("""  * added debian/compat\n""", lines)
        # First snapshot entry must have disapear
        self.assertNotIn(header1.group(0) + "\n", lines)
        # But its changelog must be included in the new one
        self.assertIn("""  * TEST-COMMITTED-SNAPSHOT\n""", lines)


    def test_dch_main_new_upstream_version_with_auto_release(self):
        """Test dch.py like git-dch script does: new upstream version - auto - release"""
        options = ["--auto", "--release"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (1.0-1) %s; urgency=low\n" % os_codename, lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_auto_snapshot(self):
        """Test dch.py like git-dch script does: new upstream version - auto - snapshot mode"""
        options = [ "--auto", "--snapshot" ]
        options.append("--snapshot")
        lines = self.run_dch(options)
        header = re.search(snap_header_1, lines[0])
        self.assertIsNotNone(header)
        self.assertEqual(header.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_snapshot_release(self):
        """Test dch.py like git-dch script does: new upstream version - snapshot - release"""
        options = ["--snapshot", "--release"]
        self.assertRaises(SystemExit, self.run_dch, options)


    def test_dch_main_new_upstream_version_with_distribution(self):
        """Test dch.py like git-dch script does: new upstream version - set distribution"""
        options = ["--distribution=testing", "--force-distribution"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (1.0-1) testing; urgency=low\n", lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_release_distribution(self):
        """Test dch.py like git-dch script does: new upstream version - release - set distribution"""
        options = ["--release", "--distribution=testing", "--force-distribution"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (1.0-1) testing; urgency=low\n", lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_snapshot_distribution(self):
        """Test dch.py like git-dch script does: new upstream version - snapshot mode - do not set distribution"""
        options = ["--snapshot", "--distribution=testing"]
        lines = self.run_dch(options)
        header = re.search(snap_header_1, lines[0])
        self.assertIsNotNone(header)
        self.assertEqual(header.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_2_snapshots_auto_distribution(self):
        """Test dch.py like git-dch script does: new upstream version - two snapshots - do not set distribution"""
        options = ["--snapshot", "--distribution=testing"]
        lines = self.run_dch(options)
        header1 = re.search(snap_header_1, lines[0])
        self.assertIsNotNone(header1)
        self.assertEqual(header1.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header1.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)
        # New snapshot, use auto to guess last one
        self.add_file("debian/compat", "9")
        options.append("--auto")
        lines = self.run_dch(options)
        header2 = re.search(snap_header_1_2, lines[0])
        self.assertIsNotNone(header2)
        self.assertEqual(header2.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header2.group(1), lines[2]))
        # First snapshot entry must be concatenated with the last one
        self.assertNotIn(header1.group(0) + "\n", lines)
        self.assertIn("""  * added debian/control\n""", lines)
        self.assertIn("""  * added debian/compat\n""", lines)
        # But its changelog must not be included in the new one since
        # we do not commit
        self.assertNotIn("""  * TEST-COMMITTED-SNAPSHOT\n""", lines)


    def test_dch_main_new_upstream_version_with_2_snapshots_commit_auto_distribution(self):
        """Test dch.py like git-dch script does: new upstream version - two committed snapshots - do not set distribution"""
        options = ["--commit"]
        options.append("--commit-msg=TEST-COMMITTED-SNAPSHOT")
        options.append("--snapshot")
        options.append("--distribution=testing")
        lines = self.run_dch(options)
        header1 = re.search(snap_header_1, lines[0])
        self.assertIsNotNone(header1)
        self.assertEqual(header1.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header1.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)
        # New snapshot, use auto to guess last one
        self.add_file("debian/compat", "9")
        options.append("--auto")
        lines = self.run_dch(options)
        header2 = re.search(snap_header_1_2, lines[0])
        self.assertIsNotNone(header2)
        self.assertEqual(header2.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header2.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)
        self.assertIn("""  * added debian/compat\n""", lines)
        # First snapshot entry must have disapear
        self.assertNotIn(header1.group(0) + "\n", lines)
        # But its changelog must be included in the new one
        self.assertIn("""  * TEST-COMMITTED-SNAPSHOT\n""", lines)


    def test_dch_main_new_upstream_version_with_urgency(self):
        """Test dch.py like git-dch script does: new upstream version - set urgency"""
        options = ["--urgency=emergency"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (1.0-1) UNRELEASED; urgency=emergency\n", lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_release_urgency(self):
        """Test dch.py like git-dch script does: new upstream version - release - set urgency"""
        options = ["--release", "--urgency=emergency"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (1.0-1) %s; urgency=emergency\n" % os_codename, lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_new_upstream_version_with_snapshot_urgency(self):
        """Test dch.py like git-dch script does: new upstream version - snapshot mode - set urgency"""
        options = ["--snapshot",  "--urgency=emergency"]
        lines = self.run_dch(options)
        header = re.search(snap_header_1, lines[0])
        self.assertIsNotNone(header)
        self.assertEqual(header.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_increment_debian_version(self):
        """Test dch.py like git-dch script does: increment debian version"""
        self.repo.delete_tag("debian/0.9-1")
        self.repo.create_tag("debian/0.9-1", msg="Pre stable release version 0.9-1", commit="HEAD~2")
        self.repo.delete_tag("upstream/1.0")
        lines = self.run_dch()
        self.assertEqual("test-package (%s) UNRELEASED; urgency=low\n" % new_version_0_9, lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_increment_debian_version_with_release(self):
        """Test dch.py like git-dch script does: increment debian version - release"""
        self.repo.delete_tag("upstream/1.0")
        options = ["--release"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (%s) %s; urgency=low\n" % (new_version_0_9, os_codename), lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_increment_debian_version_with_auto(self):
        """Test dch.py like git-dch script does: increment debian version - guess last commit"""
        self.repo.delete_tag("upstream/1.0")
        options = ["--auto"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (%s) UNRELEASED; urgency=low\n" % new_version_0_9, lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_increment_debian_version_with_snapshot(self):
        """Test dch.py like git-dch script does: increment debian version - snapshot mode"""
        self.repo.delete_tag("upstream/1.0")
        options = ["--snapshot"]
        lines = self.run_dch(options)
        header = re.search(snap_header_0_9, lines[0])
        self.assertIsNotNone(header)
        self.assertEqual(header.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_increment_debian_version_with_auto_release(self):
        """Test dch.py like git-dch script does: increment debian version - auto - release"""
        self.repo.delete_tag("upstream/1.0")
        options = ["--auto",  "--release"]
        lines = self.run_dch(options)
        self.assertEqual("test-package (%s) %s; urgency=low\n" % (new_version_0_9, os_codename), lines[0])
        self.assertIn("""  * added debian/control\n""", lines)


    def test_dch_main_increment_debian_version_with_auto_snapshot(self):
        """Test dch.py like git-dch script does: increment debian version - auto - snapshot mode"""
        self.repo.delete_tag("upstream/1.0")
        options = ["--auto",  "--snapshot"]
        lines = self.run_dch(options)
        header = re.search(snap_header_0_9, lines[0])
        self.assertIsNotNone(header)
        self.assertEqual(header.lastindex, 1)
        self.assertIsNotNone(re.search(snap_mark + header.group(1), lines[2]))
        self.assertIn("""  * added debian/control\n""", lines)
