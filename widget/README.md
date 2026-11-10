# Saat Widget'ı 🕘

*[Bandanix](../README.md) kitinin bir parçası.*

Masaüstünün ortasında büyük, ince bir saat. Altında Türkçe tarih ve tek satırda hava durumu ile sistem bilgisi:

```
                 21:31
             8 Kasım Pazar
☁ 6°C Parçalı bulutlu · Yarın 9° / 2° · İşlemci %12 · RAM %41 · 54°C
```

Bilgi satırının üzerine gelince küçük bir kutu açılır: 3 günlük tahmin, disk doluluğu ve hava durumunun en son ne zaman güncellendiği.

## Komutlar

```bash
bandanix-widget                 # şehir ve son hava durumu
bandanix-widget sehir Ankara    # şehri değiştir (aynı adda birden fazla yer varsa sorar)
bandanix-widget guncelle        # hava durumunu hemen yenile
bandanix-widget ortala          # saati ekranın ortasındaki varsayılan yerine al
```

## Nasıl çalışır

- **Saat bir Cinnamon masaüstü uygulamacığıdır (desklet).** Cinnamon'ın içinde çalışır, ayrı bir program açılmaz. Saat dakikada bir, işlemci, RAM ve sıcaklık 5 saniyede bir doğrudan sistem dosyalarından okunur.
- **Hava durumu [Open-Meteo](https://open-meteo.com)'dan gelir:** ücretsiz, hesap ya da API anahtarı istemez. Küçük bir yardımcı 30 dakikada bir veriyi alıp `~/.cache/bandanix/hava.json` dosyasına yazar; saat sadece bu dosyayı okur, yani internet yavaşken masaüstü hiç beklemez.
- İnternet yoksa son alınan bilgi gösterilmeye devam eder; iki saatten eskiyse satırın sonunda "güncellenemedi" yazar.
- Şehir kurulumda sorulur ve `~/.config/bandanix/theme.toml` içindeki `[widget]` bölümüne enlem ve boylamıyla birlikte yazılır.
- Yerini değiştirmek için saati fareyle sürükle. Yazı tipi `theme.toml`'daki `[fonts] ui` ayarından gelir; ince görünüm için yazı tipinin "Light" kalınlığı olmalı (Mint'in varsayılanı Ubuntu'da var).

## Kurulum ve kaldırma

```bash
./install.sh widget
./uninstall.sh widget
```

Kurulum, Cinnamon'ın masaüstü uygulamacıkları listesini değiştirmeden önce `bandanix-yedek` ile saklar. Kaldırınca liste eski hâline döner; saat, hava yardımcısı ve zamanlayıcısı silinir.
