# Güç Modları ❄️

*[Bandanix](../README.md) kitinin bir parçası.*

Dizüstü bilgisayarın ne kadar güç harcayacağını ve ne kadar ısınacağını tek komutla seç.

| Mod | Ne yapar | Ne için |
|---|---|---|
| **Serin** | İşlemcinin turbo'sunu kapatır | Dizi, ders, yazı. Fark edilmez ama bilgisayar belirgin şekilde serin ve sessiz kalır |
| **Eco** | MSI'ın tasarruf modu | Pilde uzun kullanım |
| **Dengeli** | MSI'ın normal modu, turbo açık | Günlük kullanım |
| **Turbo** | MSI'ın en yüksek modu | Oyun, derleme |

Neden Serin mod? Modern işlemciler en küçük işte bile birkaç saniyeliğine en yüksek hızlarına çıkar (turbo) ve tek çekirdek 90°C'yi görür. Bu tehlikeli değildir ama dizi izlerken gereksiz ısı ve fan gürültüsü demektir. Turbo kapalıyken aynı video 95°C yerine 50-55°C'de oynar.

## Komutlar

```bash
bandanix-guc                 # şu anki mod, fanlar, turbo ve sıcaklık
bandanix-guc serin           # ya da: eco, dengeli, turbo
bandanix-guc fan sessiz      # ya da: fan otomatik
bandanix-guc boost           # fanlar 5 dakika tam hız (Cooler Boost)
bandanix-guc boost kapat
```

Aynısı Bandanix Ayarlar → **Performans** bölümünde düğmelerle yapılır.

## Nasıl çalışır

- MSI dizüstülerinde güç ve fan modları `msi-ec` sürücüsüyle, turbo ise işlemcinin kendi ayarıyla değişir. MSI olmayan bilgisayarlarda sadece Serin ve Dengeli modlar görünür.
- Bu ayarları sadece yönetici yazabildiği için küçük bir yardımcı kurulur: `/usr/local/sbin/bandanix-guc-yaz`. Yardımcı **sadece dört şeyi, sadece izinli değerlerle** yazabilir: güç modu, fan modu, Cooler Boost ve turbo. Senin kullanıcın onu şifresiz çalıştırabilsin diye `/etc/sudoers.d/bandanix-guc` içine tek satırlık bir izin eklenir (eklenmeden önce `visudo` ile doğrulanır).
- Seçtiğin mod kaydedilir; küçük bir sistem servisi onu her açılışta ve uykudan uyanınca yeniden uygular.
- Cooler Boost'u 5 dakika sonra sistemin kendisi kapatır; açık unutulmaz.

## Kurulum ve kaldırma

```bash
./install.sh guc
./uninstall.sh guc
```

Kurulum hiçbir modu değiştirmez, sadece komutu hazırlar. Kaldırınca güç modu, fan modu ve turbo kurulum öncesindeki hâline döner; yardımcı, izin satırı ve servis silinir.
