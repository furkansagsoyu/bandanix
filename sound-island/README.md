# Sound Island 🏝️

*[Bandanix](../README.md) kitinin bir parçası.*

Apple'ın Dynamic Island'ından esinlenen, Linux masaüstü için yüzen bir "şimdi çalıyor" adası.
Ekranın üstünde ince bir hap olarak durur, üzerine gelince küçük bir oynatıcıya dönüşür.

<p align="center">
  <img src="../docs/sound-island-hap.png" alt="Hap modu" width="329"><br><br>
  <img src="../docs/sound-island-oynatici.png" alt="Oynatıcı modu" width="467">
</p>

**Spotify** ve [MPRIS](https://specifications.freedesktop.org/mpris-spec/latest/) destekleyen her oynatıcıyla çalışır
(VLC, Firefox, Brave, Chromium, mpv, Rhythmbox…). Spotify hesabı, API anahtarı ya da Premium gerekmez: her şey bilgisayarından okunur.

## Özellikler

- **Hap modu:** dönen albüm kapağı, şarkı adı ve sanatçı, ince bir ilerleme çizgisi ve müziğin ritmine göre zıplayan çubuklar
- **Gerçek ses çubukları:** [cava](https://github.com/karlstav/cava) ile hoparlörden çıkan sesi dinler. cava yalnızca müzik çalarken açıktır, duraklatınca kapanır; yani boştayken işlemciye yük bindirmez
- **Oynatıcı modu (üzerine gelince):** büyük kapak, oynat/duraklat, önceki/sonraki, tıklayınca o saniyeye atlayan ilerleme çubuğu
- **Senkron şarkı sözleri:** o an söylenen satır, ücretsiz [LRCLIB](https://lrclib.net) servisinden
- **Uyumlu renk:** vurgu rengi albüm kapağından seçilir (ya da Bandanix'in vurgu rengi kullanılır)
- **Yeni şarkı bildirimi:** şarkı değişince ada bir anlığına açılır
- **Ses ve parlaklık göstergesi:** ses ya da ekran parlaklığı değişince ada 1,5 saniyeliğine çubuklu bir göstergeye dönüşür (ada gizliyse sadece bunun için belirir). Cinnamon'ın kendi göstergesi kapatılır, kaldırınca geri gelir
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
bars = "auto"             # "auto" = cava ile gerçek ses, "simulated" = temsili çubuklar
gosterge = true           # ses ve parlaklık göstergesi (false = Cinnamon'ın kendi göstergesi)
```

Bu ayarlar Bandanix Ayarlar → Sound Island'dan da değiştirilebilir; orada ada kendiliğinden yeniden başlar. Dosyayı elle düzenlediysen adayı yeniden başlat; `gosterge` ayarını değiştirdiysen `./install.sh sound-island` komutunu çalıştır.

Not: cava bilgisayarın çaldığı **bütün** sesi dinler, sadece Spotify'ı değil. Aynı anda bir video açıksa çubuklar onun sesine de tepki verir.

## Sorun giderme

Şarkı sözleri gelmiyorsa adayı hata ayıklama modunda başlat, terminalde her söz isteğinin sonucu yazılır:

```bash
SOUND_ISLAND_DEBUG=1 sound-island
```

## Kaynak koddan çalıştırma (geliştirme)

```bash
sudo apt install playerctl cava python3-venv libxcb-cursor0
cd sound-island
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../ortak/ada/requirements.txt
python -m unittest discover tests
PYTHONPATH=../ortak/ada python -m sound_island
```

Qt kurulumu diğer Bandanix adalarıyla (Sistem adası) ortaktır: `~/.local/share/bandanix/ada`. Hap çizimi ve adaların yan yana dizilmesi `ortak/ada` klasöründedir.

## Yol haritası

- [x] Gerçek sese tepki veren çubuklar (cava)
- [x] Ses ve parlaklık göstergesi
- [x] Ayarlar penceresi (Bandanix Ayarlar)
- [ ] Konum ve boyut seçenekleri

Şarkı sözleri topluluk tarafından oluşturulan LRCLIB veritabanından gelir.
