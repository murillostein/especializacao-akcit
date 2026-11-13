"""Uso: python -m app <entropia_em_bits>"""

import sys

from app.tempo_quebra import avaliar_senha


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python -m app <entropia_em_bits>")
        return 2
    resultado = avaliar_senha(float(sys.argv[1]))
    status = "atende" if resultado["atende_politica"] else "NAO atende"
    print(f"Tempo medio de quebra: {resultado['tempo_legivel']} ({status} a politica)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
