# Panel Düzeni 🏝️

*[Bandanix](../README.md) kitinin bir parçası.*

Cinnamon panelini yüzen adalara çevirir. Sound Island'ın hap tasarımıyla aynı aile. İki düzen var:

- **Orta** (varsayılan, Windows 11 gibi): menü düğmesi ve açık pencereler ortada tek bir adada, sistem tepsisi ve saat sağdaki adada.
- **Üç ada:** solda menü, ortada açık pencereler, sağda tepsi ve saat.

Seçmek için `~/.config/bandanix/theme.toml` içinde `[panel]` bölümüne `duzen = "orta"` ya da `duzen = "uc-ada"` yazıp `./install.sh panel-duzeni` komutunu çalıştır.

## Nasıl çalışır

Cinnamon'da yerleşik bir "yüzen panel" özelliği yok. Ek bir eklenti ya da dock programı kullanmak yerine Cinnamon'ın kendi paneli kullanılıyor:

- Panelin zemini şeffaf yapılıyor; adalar, bölgelerin arkasına çizilen yuvarlak köşeli bir resimle oluşuyor. Bölgelerin boyutu değişmediği için ikonlar adanın tam ortasında kalıyor; pencerelerin üzerine gelince ve aktifken çıkan vurgu da adanın içinde çiziliyor.
- Pencere listesi orta bölgeye, menü düzene göre onun önüne ya da sol bölgeye alınıyor; ayırıcı kaldırılıyor. Diğer uygulamacıklar yerinde ve aynı sırada kalıyor.
- Uygulamacıkların kimlikleri değişmediği için hiçbirinin ayarı kaybolmuyor.
- Menü düğmesinin ikonu Mint logosu yerine kırmızı bandana işareti oluyor; kaldırınca Mint logosu geri gelir.
- Açık olan uygulamaların altında kısa kırmızı bir çizgi, aktif pencerede ayrıca yumuşak bir vurgu var.
- Panel yüksekliği 54 piksel oluyor (`[panel]` bölümünde `yukseklik` ile 40-64 arası ayarlanabilir); adalar bundan 12 piksel kısa, üstte ve altta kalan boşluk onları "yüzüyormuş" gibi gösteriyor.
- Sol ve orta adalardaki ikonların boyutu sabitleniyor (varsayılan 32). Değiştirmek için `theme.toml` içinde `[panel]` bölümündeki `ikon_boyutu` değerini düzenleyip `./install.sh panel-duzeni` komutunu çalıştır.

Ek program olmadığı için donma ya da kaybolma riski yok; sadece tema CSS'i değişiyor.

## Gereken

Bandanix **Cinnamon teması** kurulu olmalı, çünkü adalar o temanın üzerine eklenir. Tema yeniden üretildiğinde (örneğin vurgu rengi değişince) adalar otomatik olarak korunur.

## Kurulum ve kaldırma

```bash
./install.sh panel-duzeni
./uninstall.sh panel-duzeni
```

Kurulum, uygulamacık listesini ve panel yüksekliğini değiştirmeden önce `bandanix-yedek` ile saklar. Kaldırınca panel tam eski hâline döner.

Not: Geri alma, uygulamacık listesini kurulum öncesindeki hâline döndürür. Adalar kuruluyken panele yeni bir uygulamacık eklediysen, kaldırma sırasında o uygulamacık listeden çıkar; istersen yeniden eklersin.
