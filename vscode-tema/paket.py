#!/usr/bin/env python3
"""Pack the theme folder into a .vsix (a zip with two small manifest files) without Node or vsce.

  paket.py EKLENTI_KLASORU CIKTI.vsix
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension=".json" ContentType="application/json"/>
<Default Extension=".md" ContentType="text/markdown"/>
<Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
"""

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id={name} Version={version} Publisher={publisher}/>
    <DisplayName>{display}</DisplayName>
    <Description xml:space="preserve">{description}</Description>
    <Tags>theme,color-theme,dark</Tags>
    <Categories>Themes</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value={engine}/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value=""/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value=""/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="ui,workspace"/>
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value=""/>
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
  </Assets>
</PackageManifest>
"""


def build(folder: Path, out: Path) -> dict:
    pkg = json.loads((folder / "package.json").read_text(encoding="utf-8"))
    for theme in pkg["contributes"]["themes"]:                      # fail early on a broken theme
        json.loads((folder / theme["path"]).read_text(encoding="utf-8"))
    manifest = MANIFEST.format(
        name=quoteattr(pkg["name"]), version=quoteattr(pkg["version"]),
        publisher=quoteattr(pkg["publisher"]), display=escape(pkg["displayName"]),
        description=escape(pkg.get("description", "")), engine=quoteattr(pkg["engines"]["vscode"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("extension.vsixmanifest", manifest)
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                z.write(f, "extension/" + f.relative_to(folder).as_posix())
    return pkg


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    p = build(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"{p['publisher']}.{p['name']}")
