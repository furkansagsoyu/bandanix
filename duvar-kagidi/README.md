# Duvar Kağıtları 🖼️

*[Bandanix](../README.md) kitinin bir parçası.*

Bandana kumaşı, kırmızı gökyüzü ve BANDANIX işareti etrafında bir seri. Resimler ChatGPT ile üretildi, 1920×1080.

<p align="center">
  <img src="../docs/duvar-kagitlari.jpg" alt="Kemer, Galata, Gün Batımı ve İpek" width="100%">
</p>

| Ad | Komut |
|---|---|
| **Kemer** (varsayılan) | `bandanix-duvar kemer` |
| **Galata** | `bandanix-duvar galata` |
| **Gün Batımı** | `bandanix-duvar gunbatimi` |
| **İpek** | `bandanix-duvar ipek` |

## Komutlar

```bash
bandanix-duvar             # duvar kağıtlarını listele (kullanılan işaretli)
bandanix-duvar galata      # o duvar kağıdını kullan
```

Seçim `~/.config/bandanix/theme.toml` dosyasındaki `[duvar-kagidi]` bölümüne kaydedilir. Giriş ekranını da yeni duvar kağıdına uydurmak için `bandanix-giris guncelle`.

Arka planda hiçbir şey çalışmaz: duvar kağıdı sadece sen değiştirince değişir.

## Yeni duvar kağıdı eklemek

1. Resmi `duvar-kagidi/resimler/` klasörüne `ad.jpg` olarak koy (küçük harf, Türkçe karakter ve boşluk olmadan; ör. `kapadokya.jpg`).
2. `resimler/liste.txt` dosyasına bir satır ekle: `kapadokya = Kapadokya`
3. `./install.sh duvar-kagidi`

## Kurulum ve kaldırma

```bash
./install.sh duvar-kagidi
./uninstall.sh duvar-kagidi
```

Uygularken mevcut duvar kağıdın `bandanix-yedek` ile saklanır; kaldırınca eski duvar kağıdın geri gelir. Bandanix'in eski, kodla çizilen duvar kağıtları ve onların saatlik zamanlayıcısı kurulum sırasında kendiliğinden temizlenir.
