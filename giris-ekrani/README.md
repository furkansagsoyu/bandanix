# Giriş Ekranı 🔐

*[Bandanix](../README.md) kitinin bir parçası.*

Açılışta şifreni yazdığın ekranı (Linux Mint'in Slick Greeter'ı) masaüstüne uydurur:

- **Arka plan:** o an kullandığın duvar kağıdının hafif bulanık ve biraz koyulaştırılmış hâli. Şifre kutusu öne çıkar.
- **Görünüş:** Bandanix teması, ikonları ve imleci; 24 saatlik saat; arka plandaki nokta ızgarası kapalı. Bu parçalardan kurulu olmayan varsa Mint'in ayarı olduğu gibi kalır.

## Komutlar

```bash
bandanix-giris              # giriş ekranının şu anki ayarları
bandanix-giris guncelle     # arka planı şu anki duvar kağıdından yeniden üret (şifre ister)
bandanix-giris dene         # giriş ekranını oturumu kapatmadan bir pencerede göster
```

Duvar kağıdını değiştirdiğinde (ör. `bandanix-duvar galata`) ya da temayı yeniden kurduğunda `bandanix-giris guncelle` çalıştır; giriş ekranı da uyar.

## Nasıl çalışır

Giriş ekranı senin kullanıcınla değil, sistemin kendi kullanıcısıyla çalışır ve ev klasörünü okuyamaz. Bu yüzden:

- Arka plan `/usr/share/backgrounds/bandanix/`, tema `/usr/share/themes/Bandanix`, ikonlar ve imleç `/usr/share/icons/` altına kopyalanır. Her birine küçük bir işaret dosyası konur; kaldırırken sadece Bandanix'in koyduğu klasörler silinir.
- Ayarlar Mint'in **Giriş Penceresi** ayarlarının kullandığı `/etc/lightdm/slick-greeter.conf` dosyasına yazılır. Bandanix ilk kez dokunmadan önce dosyanın kopyası alınır.

Değişiklik bir sonraki giriş ekranında görünür: oturumu kapatınca ya da yeniden başlatınca.

## Kurulum ve kaldırma

```bash
./install.sh giris-ekrani
./uninstall.sh giris-ekrani
```

İkisi de sistem dosyalarına dokunduğu için şifre ister. Kaldırınca ayar dosyası Bandanix öncesindeki hâline döner.
