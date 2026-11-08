# Sound Island 🏝️

*[Bandanix](../README.md) kitinin bir parçası.*

Apple'ın Dynamic Island'ından esinlenen, Linux masaüstü için yüzen bir "şimdi çalıyor" adası.
Ekranın üstünde ince bir hap olarak durur, üzerine gelince küçük bir oynatıcıya dönüşür.

**Spotify** ve [MPRIS](https://specifications.freedesktop.org/mpris-spec/latest/) destekleyen her oynatıcıyla çalışır
(VLC, Firefox, Brave, Chromium, mpv, Rhythmbox…). Spotify hesabı, API anahtarı ya da Premium gerekmez: her şey bilgisayarından okunur.

## Özellikler

- **Hap modu:** dönen albüm kapağı, şarkı adı ve sanatçı, ince bir ilerleme çizgisi ve hareketli çubuklar
- **Oynatıcı modu (üzerine gelince):** büyük kapak, oynat/duraklat, önceki/sonraki, tıklayınca o saniyeye atlayan ilerleme çubuğu
- **Senkron şarkı sözleri:** o an söylenen satır, ücretsiz [LRCLIB](https://lrclib.net) servisinden
- **Uyumlu renk:** vurgu rengi albüm kapağından seçilir (ya da Bandanix'in vurgu rengi kullanılır)
- **Yeni şarkı bildirimi:** şarkı değişince ada bir anlığına açılır
- Çalan bir şey yokken kendini gizler
- Sağ tık → Çıkış

## Kurulum

Bandanix klasöründe:

```bash
./install.sh sound-island
```

Bu, uygulama menüsüne **Sound Island**'ı ve bir `sound-island` komutunu ekler, istersen girişte otomatik başlamasını da ayarlar.

Başka bir oynatıcı için `--player` kullan (isimleri `playerctl -l` gösterir):

```bash
sound-island --player vlc
```

## Ayarlar

`~/.config/bandanix/theme.toml` dosyasında:

```toml
[sound-island]
follow_cover = true       # vurgu rengini albüm kapağından al
hide_when_idle = true     # çalan bir şey yokken gizlen
```

## Kaynak koddan çalıştırma (geliştirme)

```bash
sudo apt install playerctl python3-venv libxcb-cursor0
cd sound-island
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover tests
python -m sound_island
```

## Yol haritası

- [ ] Gerçek sese tepki veren çubuklar (PipeWire / cava); çubuklar şimdilik temsili
- [ ] Daha fazla ayar: konum, boyut, hap ve söz seçenekleri
- [ ] Cinnamon panel uygulamacığı

Şarkı sözleri topluluk tarafından oluşturulan LRCLIB veritabanından gelir.
