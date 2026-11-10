"""Theme files are complete and kok.sh installs / removes them (in a test folder, with stand-in commands)."""
import os
import re
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

STUBS = {
    "update-alternatives": 'echo "update-alternatives $*" >> "$LOG"',
    "update-grub": 'echo "update-grub" >> "$LOG"; echo "Generating grub configuration file ..."; echo done',
    "update-initramfs": 'echo "update-initramfs $*" >> "$LOG"; echo "update-initramfs: Generating /boot/initrd.img"',
    # a real .pf2 starts with FILE/PFF2 and then NAME; write just enough for kok.sh to read the name
    "grub-mkfont": r'''size=16; out=""
while [ $# -gt 0 ]; do case $1 in -s) size=$2; shift;; -o) out=$2; shift;; esac; shift; done
python3 - "$out" "$size" <<'PY'
import struct, sys
name = f"DejaVu Sans Regular {sys.argv[2]}".encode() + b"\0"
open(sys.argv[1], "wb").write(b"FILE" + struct.pack(">I", 4) + b"PFF2" + b"NAME" + struct.pack(">I", len(name)) + name)
PY
echo "grub-mkfont $size" >> "$LOG"''',
}


class FilesTest(unittest.TestCase):
    def test_script_pictures_exist(self):
        script = (HERE / "plymouth" / "bandanix.script").read_text(encoding="utf-8")
        names = set(re.findall(r'(?:Image|scaled)\("([^"]+)"\)', script))
        self.assertTrue(names)
        for name in names:
            self.assertTrue((HERE / "plymouth" / name).is_file(), name)

    def test_script_brackets_balance(self):
        code = re.sub(r'"[^"]*"', '""', (HERE / "plymouth" / "bandanix.script").read_text(encoding="utf-8"))
        code = re.sub(r"//.*", "", code)
        for a, b in ("{}", "()", "[]"):
            self.assertEqual(code.count(a), code.count(b), a + b)

    def test_every_callback_is_defined(self):
        script = (HERE / "plymouth" / "bandanix.script").read_text(encoding="utf-8")
        defined = set(re.findall(r"^fun (\w+)\(", script, re.M))
        used = set(re.findall(r"Plymouth\.Set\w+Function\((\w+)\)", script))
        self.assertLessEqual(used, defined)

    def test_grub_theme_files(self):
        theme = (HERE / "grub" / "theme.txt.in").read_text(encoding="utf-8")
        self.assertIn("@FONT_ITEM@", theme)
        for name in re.findall(r'file = "([^"]+)"', theme):
            self.assertTrue((HERE / "grub" / name).is_file(), name)
        for part in ("nw", "n", "ne", "w", "c", "e", "sw", "s", "se"):
            self.assertTrue((HERE / "grub" / f"select_{part}.png").is_file(), part)
        self.assertEqual(theme.count("{"), theme.count("}"))


class KokTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.root, bin_dir, self.log = t / "kok", t / "bin", t / "log"
        for d in ("usr/share/plymouth/themes", "boot/grub", "etc/default/grub.d",
                  "usr/share/fonts/truetype/dejavu"):
            (self.root / d).mkdir(parents=True)
        (self.root / "usr/share/fonts/truetype/dejavu/DejaVuSans.ttf").write_bytes(b"x")
        bin_dir.mkdir()
        for name, body in STUBS.items():
            (bin_dir / name).write_text("#!/bin/bash\n" + body + "\n")
            (bin_dir / name).chmod(0o755)
        self.env = dict(os.environ, BANDANIX_KOK=str(self.root), LOG=str(self.log),
                        PATH=f"{bin_dir}:/usr/bin:/bin")

    def tearDown(self):
        self.tmp.cleanup()

    def run_kok(self, *args):
        return subprocess.run(["bash", str(HERE / "kok.sh"), *args], env=self.env,
                              capture_output=True, text=True, check=True).stdout

    def test_install_and_remove(self):
        out = self.run_kok("kur", str(HERE))
        ply = self.root / "usr/share/plymouth/themes/bandanix"
        self.assertTrue((ply / "bandanix.plymouth").is_file())
        self.assertTrue((ply / "wordmark.png").is_file())
        theme = (self.root / "boot/grub/themes/bandanix/theme.txt").read_text(encoding="utf-8")
        self.assertIn('item_font = "DejaVu Sans Regular 22"', theme)
        self.assertIn('terminal-font: "DejaVu Sans Regular 16"', theme)
        self.assertNotIn("@", theme)
        cfg = (self.root / "etc/default/grub.d/99-bandanix.cfg").read_text()
        self.assertIn('GRUB_THEME="/boot/grub/themes/bandanix/theme.txt"', cfg)
        log = self.log.read_text()
        self.assertIn("--set default.plymouth", log)
        self.assertIn("update-grub", log)
        self.assertTrue(log.rstrip().endswith("update-initramfs -u"))
        self.assertIn("Açılış ekranı: Bandanix", out)

        self.log.write_text("")
        self.run_kok("kaldir")
        self.assertFalse(ply.exists())
        self.assertFalse((self.root / "boot/grub/themes/bandanix").exists())
        self.assertFalse((self.root / "etc/default/grub.d/99-bandanix.cfg").exists())
        log = self.log.read_text()
        self.assertIn("--remove default.plymouth", log)
        self.assertIn("update-grub", log)
        self.assertIn("update-initramfs -u", log)

    def test_without_grub(self):
        (self.root / "boot/grub").rmdir()
        out = self.run_kok("kur", str(HERE))
        self.assertIn("GRUB bulunamadı", out)
        self.assertTrue((self.root / "usr/share/plymouth/themes/bandanix/bandanix.plymouth").is_file())

    def test_remove_when_not_installed_does_nothing(self):
        self.run_kok("kaldir")
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
