# Hızlı Not 📝

*[Bandanix](../README.md) kitinin bir parçası.*

Aklına bir şey geldiğinde iki saniyede not al: **Super+N**'ye bas, yaz, **Enter**. Kutu kaybolur, not kaydedilir.

[Sound Island](../sound-island/) çalışırken `Super+N` ilgili sekmeyi adada açar. Ada kapalıyken bu bileşenin kendi penceresi açılır.

## Kullanım

| Tuş | Ne yapar |
|---|---|
| **Super+N** | Kutuyu açar; açıkken tekrar basınca kapatır |
| **Enter** | Notu kaydeder ve kutuyu kapatır |
| **Shift+Enter** | Yeni satır (çok satırlı not) |
| **Esc** | Kaydetmeden kapatır; yazdığın kaybolmaz, bir dahaki açılışta yerinde durur |

- Yazma alanının altında son 5 not ve ne zaman yazıldıkları görünür. Bir nota tıklayınca panoya kopyalanır.
- Notu `[ ]` ile başlatırsan yapılacak iş olur. Başındaki kutucuğa tıklayınca tamamlandı olarak işaretlenir.
- Kutunun dışına tıklarsan da kapanır, taslak yine saklanır.

Terminalden:

```bash
bandanix-not "market: süt al"     # kutuyu açmadan not ekle
bandanix-not liste                # son 10 not
bandanix-not liste 30             # son 30 not
bandanix-not dosya                # not dosyasını editörde aç
```

## Notlar nerede?

Hepsi tek bir Markdown dosyasında, en yenisi en üstte: `~/Notlar/hizli-notlar.md`

```markdown
# Hızlı notlar

## 2026-11-08 20:50
[ ] Bitirme danışmanına mail at

## 2026-11-08 20:45
https://open-meteo.com
```

Dosyayı herhangi bir editörle açıp düzenleyebilirsin; kutu her açılışta dosyayı yeniden okur ve senin yazdığın satırlara dokunmaz. Dosyanın yeri ve kısayol `~/.config/bandanix/theme.toml` içindeki `[not-kutusu]` bölümünden değiştirilebilir:

```toml
[not-kutusu]
dosya = "~/Notlar/hizli-notlar.md"
kisayol = "<Super>n"
```

Kısayolu değiştirdikten sonra `./install.sh not-kutusu` komutunu çalıştır.

## Bilgisayara yük

Kutu sadece açıkken çalışır; kapanınca program tamamen kapanır, arka planda hiçbir şey kalmaz. Mint'te zaten yüklü olan GTK kullanıldığı için ayrı bir Python ortamı da kurulmaz.

## Kurulum ve kaldırma

```bash
./install.sh not-kutusu
./uninstall.sh not-kutusu
```

Super+N başka bir işe atanmışsa kurulum bunu söyler ve Ctrl+Alt+N kullanır. Kaldırınca kısayol ve komut silinir, Cinnamon'ın kısayol listesi eski hâline döner. **Notların silinmez.**
