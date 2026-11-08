<div align="center">

```
 ____      _     _   _  ____      _     _   _  ___ __  __
| __ )    / \   | \ | ||  _ \    / \   | \ | ||_ _|\ \/ /
|  _ \   / _ \  |  \| || | | |  / _ \  |  \| | | |  \  /
| |_) | / ___ \ | |\  || |_| | / ___ \ | |\  | | |  /  \
|____/ /_/   \_\|_| \_||____/ /_/   \_\|_| \_||___|/_/\_\
```

**Linux Mint için Bandana'nın masaüstü kiti.**
Birbirine yakışan küçük araçlar. İstersen hepsini kur, istersen sadece beğendiklerini.

</div>

## Parçalar

| Parça | Ne yapar |
|---|---|
| [**Sound Island**](sound-island/) | Spotify ve diğer oynatıcılar için ekranın üstünde duran "şimdi çalıyor" hapı. Üzerine gelince kontrolleri ve senkron şarkı sözleriyle küçük bir oynatıcıya dönüşür. |
| [**Terminal**](terminal/) | İki satırlı prompt (git, Python ortamı, hata kodu), bandana kırmızısı renk şeması ve her yeni pencerede `bandanix-fetch`. |

<p align="center">
  <img src="docs/sound-island-hap.png" alt="Sound Island hap modu" width="329"><br><br>
  <img src="docs/sound-island-oynatici.png" alt="Sound Island oynatıcı modu" width="467">
</p>

Yeni parçalar yolda.

## Kurulum

```bash
git clone https://github.com/furkansagsoyu/bandanix.git
cd bandanix
./install.sh
```

Kurulum bir menü açar: numara seç (`1 2`) ya da hepsi için `a` yaz.
Menüyü atlamak da mümkün:

```bash
./install.sh --all            # hepsini kur
./install.sh terminal         # sadece bir parçayı kur
```

Her şey yalnızca senin kullanıcın için kurulur (`~/.local`), her parça kendi Python ortamında çalışır.
Eksik sistem paketleri `apt` ile kurulur (şifren sorulur).

## Ortak tema

Bütün parçalar tek bir dosyayı okur: `~/.config/bandanix/theme.toml`

```toml
[colors]
accent = "#C8102E"        # bandana kırmızısı

[fonts]
ui = ""                   # boş = sistemin yazı tipi
```

Bir kere değiştir, bütün parçalar uysun. Yeniden kurulum yaptığın değişiklikleri asla silmez.

## Kaldırma

```bash
./uninstall.sh                  # menü
./uninstall.sh --all            # hepsini kaldır, tema dosyası kalsın
./uninstall.sh --all --purge    # tema dosyası dahil her şeyi kaldır
```

## Test edildiği sistem

Linux Mint 22 (Cinnamon, X11). X11 kullanan diğer Debian/Ubuntu tabanlı masaüstlerinde de çalışması beklenir.

## Notlar

Furkan Sağsoyu (Bandana) tarafından, bir yapay zekâ asistanının (Claude) yardımıyla geliştirildi.
Spotify, Apple ya da Linux Mint ile bir bağlantısı yoktur.

## Lisans

MIT
