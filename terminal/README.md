# Terminal 🖥️

*[Bandanix](../README.md) kitinin bir parçası.*

Terminali Bandanix'e çeviren paket: iki satırlı bir prompt, bandana kırmızısı bir renk şeması ve her yeni pencerede sistem bilgisini gösteren `bandanix-fetch`.

Örnek görünüm:

```
  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄    bandana@furkan
  ▀█▓░▓░▓░▓░▓░▓█▀    ──────────────
    ▀█▓░▓░▓░▓█▀      Sistem   Linux Mint 22 · Cinnamon
      ▀█▓░▓█▀        Çekirdek 6.8.0-49
        ▀█▀          Açık     2 sa 14 dk
                     Paket    2143 apt · 12 flatpak
                     CPU      Intel Core i7-13620H
                     GPU      NVIDIA GeForce RTX 4060
                     Bellek   6.1 / 15.5 GB
                     Disk     120 / 476 GB
                     Pil      %98 · şarjda
                     Çalıyor  Free Bird · Lynyrd Skynyrd

╭─ ~/bandanix  ⎇ main ●  🐍 base
╰─❯
```

## Prompt

- **Klasör** Bandanix kırmızısıyla, ev dizini `~` olarak
- **Git dalı**, commit edilmemiş değişiklik varsa `●`
- **Python ortamı** (conda ya da venv); `.venv` yerine projenin adı görünür
- **Hata kodu:** son komut başarısız olduysa `╰─✗ 127 ❯`
- Kullanıcı ve bilgisayar adı yalnızca SSH bağlantısında görünür
- Ek program gerektirmez, saf bash

## bandanix-fetch

- Her yeni terminal penceresinde bir kez gösterilir; VS Code terminalinde, SSH'ta ve iç içe kabuklarda gösterilmez
- `bandanix-fetch --big` büyük BANDANIX logosuyla gösterir
- Hızlıdır (~0,02 sn): işlemci ve ekran kartı modeli günde bir kez hesaplanıp önbelleğe alınır
- "Çalıyor" satırı yalnızca müzik çalarken görünür

## Renk şeması

Kurulum GNOME Terminal'e ayrı bir **"Bandanix"** profili ekler ve varsayılan yapar. Eski profilin silinmez; kaldırınca yeniden varsayılan olur.

## Kurulum

Bandanix klasöründe:

```bash
./install.sh terminal
```

Kurulum `~/.bashrc` dosyasının yedeğini alır ve sonuna işaretli tek bir blok ekler. Kaldırma (`./uninstall.sh terminal`) sadece o bloğu siler.

## Ayarlar

`~/.config/bandanix/theme.toml` dosyasında:

```toml
[colors]
accent = "#C8102E"        # prompt ve fetch bu rengi kullanır

[terminal]
prompt = true             # Bandanix prompt'u
fetch_on_open = true      # açılışta bandanix-fetch
```

Değişiklikler yeni açılan terminallerde geçerli olur. İmleç rengini de değiştirmek için `./install.sh terminal` komutunu tekrar çalıştır.
