import yaml
import pandas as pd

def load_config(path="./config.yaml"):
    # Read YAML config file
    with open(path, "r") as stream:
        config = yaml.safe_load(stream)
    return config