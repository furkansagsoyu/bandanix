# Bandanix Ayarlar ⚙️

*[Bandanix](../README.md) kitinin bir parçası.*

Bütün Bandanix ayarları tek pencerede. Menüde **Bandanix Ayarlar**, terminalde `bandanix`.

| Bölüm | Ne var |
|---|---|
| **Görünüm** | Vurgu rengi ve yazı tipi. "Uygula" tema, ikonlar, imleç, panel, saat ve adaları yeni renkle yeniden üretir (bir dakika kadar sürer, altta ilerleme görünür). |
| **Duvar kağıdı** | Önizlemeye tıkla, hemen uygulanır. "Giriş ekranına da uygula" giriş ekranını da uydurur. |
| **Panel** | Düzen (Orta / Üç ada), panel yüksekliği, ikon boyutu. |
| **Sound Island** | Albüm kapağı rengi, boşta gizlenme, ses çubukları, ses ve parlaklık göstergesi. Ada kendiliğinden yeniden başlar. |
| **Sistem adası ve saat** | Uyarı sınırları; hava durumu şehrini arayıp seçme. |
| **Pil** | Şarj sınırı kaydırıcısı, düşük pil uyarısı, pilin durumu ve sağlığı. |
| **Performans** | Güç modu (Serin, Eco, Dengeli, Turbo), fan modu, Cooler Boost. |
| **Kısayollar** | Not kutusu ve pano kısayolları; yeni tuşa basarak değiştirilir, dolu tuşlar için uyarır. |
| **Parçalar** | Hangi parça kurulu; tek tıkla kur ya da kaldır (şifre ya da onay gerekebileceği için terminal penceresinde çalışır). |
| **Yedekler** | Masaüstü yedekleri; yedek al ya da geri yükle. |

Ayarlar `~/.config/bandanix/theme.toml` dosyasına yazılır; dosyayı elle düzenlemek de çalışmaya devam eder, yorum satırların korunur.

Kurulu olmayan bir parçanın bölümünde onun yerine bir **Kur** düğmesi görünür.

## Bandanix klasörü

Kurma, kaldırma ve renk değiştirme, Bandanix klasöründeki (`git clone` ile indirdiğin, genelde `~/bandanix`) kurulum dosyalarını kullanır. Klasörün yeri kurulumda not edilir. Klasörü taşırsan yeni yerinde bir kez `./install.sh ayarlar` çalıştır.

## Bilgisayara yük

Uygulama sadece açıkken çalışır; kapatınca hiçbir şey kalmaz. Mint'te zaten yüklü olan GTK kullanılır, ek kurulum gerekmez.

## Kurulum ve kaldırma

```bash
./install.sh ayarlar
./uninstall.sh ayarlar
```

Kaldırmak sadece uygulamayı siler; parçalar ve ayarların yerinde kalır.
