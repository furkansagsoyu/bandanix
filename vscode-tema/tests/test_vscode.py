"""The theme file is valid, every colour is a hex value, and the .vsix has what VS Code expects."""
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.dom import minidom

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import paket  # noqa: E402

EXT = HERE / "eklenti"
HEX = re.compile(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?")


def luminance(colour: str) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class ThemeTest(unittest.TestCase):
    def setUp(self):
        self.pkg = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
        self.theme = json.loads((EXT / self.pkg["contributes"]["themes"][0]["path"]).read_text(encoding="utf-8"))

    def test_package(self):
        self.assertEqual((self.pkg["publisher"], self.pkg["name"]), ("furkansagsoyu", "bandanix-dark"))
        self.assertEqual(self.pkg["contributes"]["themes"][0]["uiTheme"], "vs-dark")
        self.assertEqual(self.theme["type"], "dark")

    def test_every_colour_is_hex(self):
        for key, value in self.theme["colors"].items():
            self.assertRegex(value, HEX, key)
            self.assertTrue(HEX.fullmatch(value), key)
        for rule in self.theme["tokenColors"]:
            fg = rule["settings"].get("foreground")
            if fg is not None:
                self.assertTrue(HEX.fullmatch(fg), rule.get("name"))

    def test_code_is_readable(self):
        bg = self.theme["colors"]["editor.background"]
        self.assertGreaterEqual(contrast(self.theme["colors"]["editor.foreground"], bg), 7)
        for rule in self.theme["tokenColors"]:
            fg = rule["settings"].get("foreground")
            if fg:
                self.assertGreaterEqual(contrast(fg[:7], bg), 4.5, rule.get("name"))

    def test_vsix(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "t.vsix"
            paket.build(EXT, out)
            with zipfile.ZipFile(out) as z:
                names = set(z.namelist())
                self.assertLessEqual({"extension.vsixmanifest", "[Content_Types].xml", "extension/package.json",
                                      "extension/themes/bandanix-dark-color-theme.json"}, names)
                doc = minidom.parseString(z.read("extension.vsixmanifest"))
                minidom.parseString(z.read("[Content_Types].xml"))
            ident = doc.getElementsByTagName("Identity")[0]
            self.assertEqual((ident.getAttribute("Publisher"), ident.getAttribute("Id"), ident.getAttribute("Version")),
                             ("furkansagsoyu", "bandanix-dark", self.pkg["version"]))


if __name__ == "__main__":
    unittest.main()
