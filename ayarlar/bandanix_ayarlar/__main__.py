"""Entry point: `python3 -m bandanix_ayarlar` (the `bandanix` command)."""
import sys

USAGE = """Kullanım:
  bandanix              Bandanix Ayarlar penceresini açar
  bandanix guncelle     GitHub'dan güncellemeleri al, değişen parçaları yeniden kur
  bandanix durum        güncelleme var mı (GitHub'a da bakar)"""


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help", "yardim"):
        print(USAGE)
        return 0
    if args and args[0] in ("guncelle", "durum"):
        from . import ortam
        guncelle = ortam.core_module("bandanix_guncelle")
        if guncelle is None:
            print("• Bandanix klasörü bulunamadı. Klasörde bir kez ./install.sh çalıştır.")
            return 1
        return guncelle.main(["guncelle"] if args[0] == "guncelle" else ["durum", "--fetch"])
    if args:
        print(USAGE, file=sys.stderr)
        return 2
    from .pencere import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
