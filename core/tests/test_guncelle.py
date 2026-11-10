"""bandanix guncelle: fingerprints, pending parts, pulling only from a clean clone."""
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent


def sh(*args, cwd=None, env=None):
    return subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout


class GuncelleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.home = t / "home"
        self.home.mkdir()
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}
        # the "GitHub" side
        self.origin = t / "origin"
        (self.origin / "core").mkdir(parents=True)
        shutil.copy(CORE / "bandanix_guncelle.py", self.origin / "core")
        (self.origin / "scripts").mkdir()
        (self.origin / "scripts/lib.sh").write_text("# lib\n")
        (self.origin / "ortak/ada").mkdir(parents=True)
        (self.origin / "ortak/ada/lib.py").write_text("v1")
        # a top-level installer that installs by touching the marker and records like the real one
        (self.origin / "install.sh").write_text(textwrap.dedent('''\
            #!/bin/bash
            for c in "$@"; do touch "$HOME/kurulu-$c"; echo "kuruldu $c" >> "$HOME/log"
              /usr/bin/python3 "$(dirname "$0")/core/bandanix_guncelle.py" kaydet "$c"; done
        '''))
        for part, extra in (("a", ""), ("b", "source ortak/ada/kur.sh\n"), ("c", "")):
            (self.origin / part).mkdir()
            (self.origin / part / "install.sh").write_text(f"#!/bin/bash\n# description: {part}\n# kurulu: ~/kurulu-{part}\n{extra}")
            (self.origin / part / "dosya.txt").write_text("1")
            (self.origin / part / "README.md").write_text("readme")
        for f in self.origin.rglob("install.sh"):
            f.chmod(0o755)
        sh("git", "init", "-q", "-b", "main", cwd=self.origin, env=self.env)
        sh("git", "add", "-A", cwd=self.origin, env=self.env)
        sh("git", "commit", "-qm", "ilk", cwd=self.origin, env=self.env)
        # the user's clone, with a and b installed
        self.repo = self.home / "bandanix"
        sh("git", "clone", "-q", str(self.origin), str(self.repo), env=self.env)
        sh(str(self.repo / "install.sh"), "a", "b", env=self.env)

    def tearDown(self):
        self.tmp.cleanup()

    def run_g(self, *args):
        return subprocess.run(["/usr/bin/python3", str(self.repo / "core/bandanix_guncelle.py"), *args],
                              env=self.env, capture_output=True, text=True)

    def status(self, *extra):
        return json.loads(self.run_g("durum", "--json", *extra).stdout)

    def commit_origin(self, path, text):
        (self.origin / path).write_text(text)
        sh("git", "commit", "-qam", "değişiklik", cwd=self.origin, env=self.env)

    def test_fresh_install_is_up_to_date(self):
        st = self.status()
        self.assertEqual((st["degisen"], st["kayitsiz"], st["kirli"], st["geride"]), ([], [], False, 0))

    def test_readme_and_tests_do_not_count(self):
        self.commit_origin("a/README.md", "yeni readme")
        self.assertEqual(self.status("--fetch")["geride"], 1)
        self.run_g("guncelle")
        self.assertEqual(self.status()["degisen"], [])
        self.assertNotIn("kuruldu a\nkuruldu a", (self.home / "log").read_text())

    def test_pull_then_reinstall_only_changed_installed_parts(self):
        self.commit_origin("a/dosya.txt", "2")
        self.commit_origin("c/dosya.txt", "2")          # c is not installed: left alone
        self.commit_origin("ortak/ada/lib.py", "v2")    # b uses the shared island library
        self.assertEqual(self.status("--fetch")["geride"], 3)
        (self.home / "log").write_text("")
        r = self.run_g("guncelle")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.home / "log").read_text().split(), ["kuruldu", "a", "kuruldu", "b"])
        st = self.status()
        self.assertEqual((st["degisen"], st["geride"]), ([], 0))
        self.assertIn("Her şey güncel", self.run_g("guncelle").stdout)

    def test_local_changes_skip_pull(self):
        self.commit_origin("c/dosya.txt", "2")
        (self.repo / "a/dosya.txt").write_text("yerel")
        st = self.status("--fetch")
        self.assertEqual((st["kirli"], st["degisen"], st["geride"]), (True, ["a"], 1))
        (self.home / "log").write_text("")
        out = self.run_g("guncelle").stdout
        self.assertIn("çekme atlandı", out)
        self.assertEqual((self.home / "log").read_text().split(), ["kuruldu", "a"])
        self.assertEqual(self.status()["geride"], 1)    # still behind: nothing was pulled

    def test_parts_installed_before_records_existed(self):
        shutil.rmtree(self.home / ".local/share/bandanix/kurulum")
        st = self.status()
        self.assertEqual(sorted(st["kayitsiz"]), ["a", "b"])
        out = self.run_g("guncelle").stdout
        self.assertIn("İlk kez", out)
        self.assertEqual(self.status()["kayitsiz"], [])
        self.assertTrue((self.home / ".local/share/bandanix/core/bandanix_guncelle.py").is_file())

    def test_not_a_clone(self):
        shutil.rmtree(self.repo / ".git")
        st = self.status("--fetch")
        self.assertEqual((st["git"], st["geride"]), (False, None))
        self.assertIn("git klasörü değil", self.run_g("guncelle").stdout)


if __name__ == "__main__":
    unittest.main()
