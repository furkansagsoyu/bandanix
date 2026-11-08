# Cinnamon Teması 🎨

*[Bandanix](../README.md) kitinin bir parçası.*

Pencereleri, menüleri, dosya yöneticisini ve Cinnamon panelini Bandanix renklerine çeviren koyu tema.

## Nasıl çalışır

Tema sıfırdan çizilmiyor: kurulum, Mint'in kendi **Mint-Y-Dark-Red** temasını kopyalayıp renklerini Bandanix paletine taşıyor ve sonucu `~/.themes/Bandanix` klasörüne koyuyor.

- Sistem dosyalarına dokunulmaz, şifre gerekmez
- Mint uygulamalarıyla birebir uyumlu kalır
- Derleme aracı gerekmez; üretim birkaç saniye sürer
- Kırmızılar bandana kırmızısına, koyu griler Bandanix tonlarına geçer; yeşil, mavi gibi diğer renklere dokunulmaz

## Kapsam

GTK3 ve GTK2 uygulamaları, Cinnamon (panel, menü, bildirimler, Alt+Tab, göstergeler) ve GTK4/libadwaita uygulamalarının vurgu rengi.

Pencere kenarlıkları değiştirilmez: Mint-Y'nin bütün renk varyantları ortak "Mint-Y" kenarlığını kullanır, Bandanix de onu kullanmaya devam eder. Başlık çubuğunu kendisi çizen uygulamalarda (çoğu GTK3 uygulaması) başlık ve düğmeler Bandanix renklerini alır.

VS Code, Spotify, Discord gibi Electron uygulamaları kendi görünümlerini kullanır ve temadan etkilenmez.

## Renkler

| Kullanım | Renk |
|---|---|
| Panel, en koyu zemin | `#121214` |
| Pencere zemini | `#17171A` |
| Kenar çubuğu, kartlar | `#1C1C1F` |
| Metin | `#E8E6E3` |
| Vurgu | `#C8102E` |

Vurgu rengi `~/.config/bandanix/theme.toml` dosyasındaki `accent` değerinden okunur. Değiştirdikten sonra temayı yeniden üretmek için:

```bash
./install.sh cinnamon-tema
```

## Kurulum ve kaldırma

```bash
./install.sh cinnamon-tema
./uninstall.sh cinnamon-tema
```

Kurulum temayı ürettikten sonra uygulansın mı diye sorar. Uygularken değiştirdiği her ayarın eski değerini `bandanix-yedek` ile saklar; kaldırınca yalnızca bu ayarlar eski hâline döner.

Mint bir güncellemeyle Mint-Y'yi yenilerse aynı kurulum komutu Bandanix'i yeni sürümün üzerine tekrar üretir.

## Lisans

Bu tema Linux Mint'in [mint-themes](https://github.com/linuxmint/mint-themes) projesinden türetilir; üretilen tema dosyaları o projenin lisansına tabidir. Bandanix'in kendi kodu MIT lisanslıdır.
