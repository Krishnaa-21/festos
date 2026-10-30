# OWNER: P1
import logging
import sys

from app.seed.registry import run_seeders

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "load"
    if action == "reset":
        print("Resetting database and running seeders...")
        run_seeders(reset=True)
    elif action == "load":
        print("Ensuring tables and running seeders...")
        run_seeders(reset=False)
    else:
        print(f"Unknown action: {action}. Use 'reset' or 'load'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
