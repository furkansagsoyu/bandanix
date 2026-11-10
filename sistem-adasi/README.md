# Sistem Adası 🌡️

*[Bandanix](../README.md) kitinin bir parçası.*

Bilgisayarın iyiyken **görünmez**. İşlemci uzun süre çok yüklenince, sıcaklık yükselince, RAM dolunca ya da disk dolmak üzereyken ekranın üstünde, Sound Island'ın yanında küçük bir hap belirir. Durum düzelince kendiliğinden kaybolur.

## Ne zaman belirir?

| Ölçüm | Sınır |
|---|---|
| İşlemci | 1 dakika boyunca ortalama %90'ın üstünde |
| Sıcaklık | 30 saniyelik ortalaması 90°C'nin üstünde (en sıcak işlemci sensörü). İşlemcinin birkaç saniyelik turbo sıçramaları uyarı vermez. |
| RAM | %90'ın üstünde dolu |
| Disk | %95'ten dolu (kök bölüm; ev klasörü ayrı diskteyse o da) |

Hapın kaybolması için değerin sınırın 5 puan altına inmesi gerekir; böylece sınırın etrafında gidip gelen bir değer hapı yanıp söndürmez. Sınırlar `~/.config/bandanix/theme.toml` içindeki `[sistem-adasi]` bölümünden değiştirilebilir.

## Hapın üzerine gelince

- Dört ölçüm küçük çubuklarla görünür; sınırı aşan bandana kırmızısıdır.
- Sorun işlemci ya da sıcaklıksa en çok işlemci kullanan, RAM ise en çok RAM kullanan 3 program listelenir. Her birinin yanında **Kapat** düğmesi vardır: ilk tıklama "Emin misin?" diye sorar, ikinci tıklama programı kapatır. Program 3 saniye içinde kapanmazsa düğme **Zorla kapat** olur.
- Sadece senin kullanıcına ait programlar kapatılabilir; masaüstünün kendisi (Cinnamon, ses sistemi gibi) ve sistem programları için düğme çıkmaz.
- Sorun diskse boş alan ve Disk Kullanım Çözümleyicisi'ni açan bir düğme görünür.
- Sağ tık: **1 saat sustur** ya da **Düzelene kadar gizle**.

## Komutlar

```bash
bandanix-sistem          # şu anki değerler ve sınırlar
bandanix-sistem dene     # adayı 20 saniyeliğine örnek bir uyarıyla göster
bandanix-sistem ac       # izlemeyi aç
bandanix-sistem kapat    # izlemeyi kapat
```

## Bilgisayara yük

İki küçük parçadan oluşur:

- **Bekçi:** Qt kullanmayan küçük bir Python programı. Oturum açılınca başlar, 5 saniyede bir sistemin kendi dosyalarından (`/proc`, `/sys`) okur. 10 MB civarı RAM kullanır.
- **Hap:** Sadece bir sorun varken açılır, sorun bitince program tamamen kapanır.

Hap, Sound Island ile aynı Qt kurulumunu paylaşır (`~/.local/share/bandanix/ada`); ikisi birlikte kuruluysa Qt diske bir kere iner.

## Kurulum ve kaldırma

```bash
./install.sh sistem-adasi
./uninstall.sh sistem-adasi
```
