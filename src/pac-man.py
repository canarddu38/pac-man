#!/usr/bin/env python3

from graphics import Graphics
from config import parser, ParserException
import sys


def main() -> None:
    path: str = sys.argv[1]
    config = parser(path)

    graphic = Graphics(config=config)
    graphic.run()


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ParserException(
                f"Usage: python3 {sys.argv[0]} path/to/config.json"
            )
        main()
    except ParserException as e:
        e.pretty_print()
    except Exception as e:
        print("An error occurred:", e)
