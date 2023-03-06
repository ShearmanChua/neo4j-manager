import json
import requests
import torch
import numpy as np
import pandas as pd
import streamlit as st

from utils import neo4jManager
from utils import utils

config = utils.load_config()
st.sidebar.title(config["sidebar_title"])

# sidebar dropdown selection
action = st.sidebar.selectbox(
    "Select action", ("👮 Admin", "📈 Node Population", "🔀 Relation Population")
)

st.sidebar.markdown("---")

neo4j_db = config["neo4j_db"]


