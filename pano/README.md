# Pano Geçmişi 📋

*[Bandanix](../README.md) kitinin bir parçası.*

Kopyaladığın yazıların listesi, Windows 11'deki Win+V gibi. **Super+V**'ye bas, aradığını seç, Enter: seçtiğin yazı bulunduğun pencereye yapıştırılır.

## Kullanım

| Tuş | Ne yapar |
|---|---|
| **Super+V** | Listeyi açar; açıkken tekrar basınca kapatır |
| *yazmak* | Listeyi süzer (Türkçe harfler doğru eşleşir: "istanbul" → "İstanbul") |
| **↑ ↓** | Seçimi değiştirir |
| **Enter** | Seçileni yapıştırır (terminallerde Ctrl+Shift+V, diğer pencerelerde Ctrl+V ile) |
| **Delete** | Seçileni siler (arama kutusu boşken) |
| **Esc** | Kapatır |

- Bir satırın üzerine gelince **📌** (sabitle) ve **✕** (sil) düğmeleri çıkar. Sabitlenenler hep listenin üstünde durur; e-posta adresi, IBAN gibi sık kullandıkların için.
- En alttaki **Geçmişi temizle** iki adımda onay ister ve sabitlenmemiş her şeyi siler.

Terminalden:

```bash
bandanix-pano liste      # geçmişi göster
bandanix-pano temizle    # sabitlenmemiş bütün geçmişi sil
```

## Gizlilik

- Geçmiş `~/.local/share/bandanix/pano.json` dosyasında durur; dosyayı sadece senin kullanıcın okuyabilir.
- Son **50** kopyalama tutulur (sabitlenenler bu sayıya dahil değil).
- Şifre yöneticileri (KeePassXC gibi) şifreyi panoya "geçmişe alma" işaretiyle koyar; bu işaretli kopyalamalar **hiç kaydedilmez**.
- Resimler, dosyalar, boş ve 20.000 karakterden uzun kopyalamalar alınmaz.
- Kaldırınca geçmiş dosyası da silinir.

## Bilgisayara yük

Panoyu izlemek için küçük bir bekçi oturum boyunca çalışır (20-25 MB RAM). Sadece bir şey kopyalandığında uyanır, onun dışında işlemci kullanmaz. Liste kutusu ise sadece açıkken çalışır.

## Kurulum ve kaldırma

```bash
./install.sh pano
./uninstall.sh pano
```

Super+V başka bir işe atanmışsa kurulum bunu söyler ve Ctrl+Alt+V kullanır. Kısayolu `~/.config/bandanix/theme.toml` içindeki `[pano]` bölümünden değiştirebilirsin.
