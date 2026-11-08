# Pil Sağlığı 🔋

*[Bandanix](../README.md) kitinin bir parçası.*

Lityum piller hep %100'de beklediğinde daha çabuk yıpranır. Dizüstü bilgisayar çoğu zaman prize takılı duruyorsa şarjı %80'de durdurmak pilin ömrünü belirgin şekilde uzatır. Bu parça:

- Şarjı **%80'de durdurur.** Sınırı pilin kendisi uygular, yani bilgisayar kapalıyken ya da uykudayken de geçerli.
- Pil **%20'nin altına inince** bir bildirim gösterir (her düşüşte bir kere, sürekli rahatsız etmez).
- Yolculuk öncesi gibi durumlar için **bir seferlik tam şarj** verir; pil dolunca ya da şarj aletini çıkarınca sınır kendiliğinden geri gelir.

## Komutlar

```bash
bandanix-pil              # durum: şarj, kalan süre, pil sağlığı, döngü sayısı, sınır
bandanix-pil tam          # bu seferlik %100'e kadar şarj et
bandanix-pil sinir 85     # sınırı değiştir (50-100)
```

`bandanix-pil` çıktısı şöyle görünür:

```
Pil         %57  (pilden çalışıyor)
Kalan       yaklaşık 2 sa 30 dk
Sağlık      %92  (şimdi 48.2 Wh, ilk hâli 52.4 Wh)
Döngü       213
Sınır       %80
Uyarı       %20 altına inince
```

Sınır ve uyarı yüzdeleri `~/.config/bandanix/theme.toml` içindeki `[pil]` bölümünde durur (`ust` ve `alt`).

## Nasıl çalışır

- Şarj sınırı Linux'un standart `charge_control_end_threshold` ayarıyla yazılır. MSI dizüstülerinde bunu `msi-ec` sürücüsü sağlar; ThinkPad, ASUS, Dell, Huawei gibi pek çok başka marka da aynı ayarı destekler.
- Bu ayarı sadece yönetici yazabildiği için küçük bir yardımcı kurulur: `/usr/local/sbin/bandanix-pil-yaz`. Bu yardımcı **tek bir dosyaya, sadece 50 ile 100 arası bir sayı** yazabilir, başka hiçbir şey yapamaz. Senin kullanıcın onu şifresiz çalıştırabilsin diye `/etc/sudoers.d/bandanix-pil` içine tek satırlık bir izin eklenir (eklenmeden önce `visudo` ile doğrulanır).
- Bazı bilgisayarlar açılışta ya da uykudan uyanınca sınırı sıfırlar. Bunun için küçük bir sistem servisi sınırı her açılışta ve uyanışta yeniden uygular.
- Düşük pil kontrolü iki dakikada bir çalışan bir kullanıcı zamanlayıcısıdır; birkaç dosya okuyup kapanır, arka planda sürekli çalışan bir program yoktur.
- Bilgisayarın şarj sınırını desteklemiyorsa sınır kısmı kurulmaz; onun yerine şarj %80'e gelince "şarj aletini çıkarabilirsin" bildirimi gelir.

## Kurulum ve kaldırma

```bash
./install.sh pil
./uninstall.sh pil
```

Kurulum, sınırı değiştirmeden önce eski değeri saklar. Kaldırınca sınır eski değerine döner; yardımcı, izin satırı ve servis silinir.
