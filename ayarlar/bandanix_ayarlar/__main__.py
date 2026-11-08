"""Entry point: `python3 -m bandanix_ayarlar` (the `bandanix` command)."""
import sys


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "yardim"):
        print("Kullanım: bandanix    Bandanix Ayarlar penceresini açar")
        return 0
    from .pencere import run
    return run()


if __name__ == "__main__":
    sys.exit(main())
