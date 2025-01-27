import tomllib
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "configs.toml"

def load_config():
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)

configs = load_config() 