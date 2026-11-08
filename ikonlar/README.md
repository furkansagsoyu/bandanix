# İkonlar ve İmleç 📁

*[Bandanix](../README.md) kitinin bir parçası.*

Bandana kırmızısı klasörler ve siyah gövdeli, kırmızı kenarlı bir fare imleci.

<p align="center">
  <img src="../docs/ikonlar-klasorler.png" alt="Bandanix klasör ikonları" width="584"><br><br>
  <img src="../docs/ikonlar-imlec.png" alt="Bandanix imleci" width="368">
</p>

## İkonlar

Mint'in **Mint-Y-Red** ikon teması kopyalanıp kırmızıları bandana kırmızısına çevrilir ve `~/.local/share/icons/Bandanix` olarak kurulur.

- Sadece kırmızılar değişir: klasörler, ev, masaüstü, indirilenler gibi yer ikonları. Gri tonlara dokunulmaz, çünkü ikonlara derinliği onlar verir.
- Diğer bütün ikonlar (uygulamalar, dosya türleri, sistem) Mint-Y'den aynen gelir.

## İmleç

**Bibata-Modern-Classic** temel alınır: siyah gövde kalır, beyaz kenar bandana kırmızısına döner. `~/.icons/Bandanix-Imlec` olarak kurulur (imleç kütüphanesinin her sistemde baktığı klasör).

- Kenar yumuşatması korunur; ara tonlar siyahla kırmızı arasında kademeli geçer.
- Bekleme animasyonu gibi hareketli imleçler de boyanır.
- Renkli parçalar olduğu gibi kalır: kopyalama imlecindeki yeşil "+", yasak işaretinin içi, bilgi rozeti gibi. Sadece imlecin dış kenarına bağlı gri tonlar kırmızıya döner.
- İmleç boyutu değişmez. Masaüstü arka planı gibi yerler için sistemin varsayılan imleci de Bandanix'e yönlendirilir.

## Kurulum ve kaldırma

```bash
./install.sh ikonlar
./uninstall.sh ikonlar
```

Kurulum ikonların ve imlecin uygulanıp uygulanmayacağını ayrı ayrı sorar. Uygularken değiştirdiği ayarların eski değerini `bandanix-yedek` ile saklar; kaldırınca yalnızca bu ayarlar eski hâline döner.

Üretim birkaç saniye sürer; imleç dosyaları işlemcinin bütün çekirdeklerine paylaştırılır. Vurgu rengi `~/.config/bandanix/theme.toml` dosyasındaki `accent` değerinden okunur; değiştirdikten sonra `./install.sh ikonlar` ile yeniden üretilir.

Gerekenler: `mint-y-icons`, `bibata-cursor-theme` (Mint'te yüklü gelir) ve `python3-pil` (yoksa kurulum kendisi kurar).

## Lisans

İkonlar Linux Mint'in Mint-Y ikon temasından, imleç [Bibata](https://github.com/ful1e5/Bibata_Cursor) imleç temasından türetilir; üretilen dosyalar kaynak projelerin lisanslarına tabidir. Bandanix'in kendi kodu MIT lisanslıdır.
