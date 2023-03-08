import json
import requests
import numpy as np
import pandas as pd
import streamlit as st

from utils import neo4jManager
from utils import utils

config = utils.load_config()
st.sidebar.title(config["sidebar_title"])

# sidebar dropdown selection
action = st.sidebar.selectbox(
    "Select action", ("💽 Load data", "📈 Node Population", "🔀 Relation Population", "👮 Admin")
)

st.sidebar.markdown("---")

###############################################
# 💽 Load data
################################################

if action == "💽 Load data":
     # upload file
    uploaded_file = st.sidebar.file_uploader("Upload CSV / excel")

    # enter absolute file path
    uploaded_file_path = st.sidebar.text_input("Enter absolute filepath to CSV")

    ################################################
    # Read csv to DataFrame
    ################################################
    # initialise dataframe
    df = pd.DataFrame()

    if uploaded_file or uploaded_file_path:
        if uploaded_file.name.endswith("csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith("xlsx"):
            df = pd.read_excel(uploaded_file)

        df["source_file"] = uploaded_file.name
        filename = uploaded_file.name

    if df.empty and "dataframe" in st.session_state:
        st.dataframe(st.session_state["dataframe"])
    else:
        st.dataframe(df)
    load_data = st.sidebar.button('Load Data')

    if load_data:
        st.session_state["dataframe"] = df
        st.success('Loaded Data from {}'.format(uploaded_file.name))

################################################
# ✨ Node Population
################################################
elif action == "📈 Node Population":
    if "dataframe" in st.session_state:
        cache_df = st.session_state["dataframe"]

        st.dataframe(cache_df)
        node_id_field = st.selectbox("Column as node_id", list(cache_df.columns))
        node_collection = st.text_input('Node Collection')
        node_labels = st.text_input("Node labels (If multiple node labels, please deliminate by comma ',' )")

        populate_nodes = st.button('Populate nodes')

        if populate_nodes:
            assert len(cache_df[node_id_field]) == len(cache_df[node_id_field].unique()), "x should be 'hello'"
            if node_labels != '':
                node_labels = node_labels.split(',')
            else:
                node_labels = []
            nodes = {}
            nodes['node_collection'] = node_collection
            nodes['node_labels'] = node_labels
            nodes['node_id_field'] = node_id_field
            cache_df = cache_df.fillna('No Data')
            nodes['nodes'] = cache_df.to_dict('records')

            response = requests.post(config["neo4j_api"] + "/create_nodes", json=nodes)
            st.info(response)

elif action == "🔀 Relation Population":
    node_types_response = requests.post(config["neo4j_api"] + "/get_nodes")
    node_types = node_types_response.json()['node_types']

    st.write('Nodes in neo4j DB: {}'.format(node_types))

    source_node = st.selectbox("Source Node", node_types)
    target_node = st.selectbox("target Node", node_types)

    source_node_properties_response = requests.post(config["neo4j_api"] + "/get_node_properties", json={'node_type':source_node})
    source_node_properties = source_node_properties_response.json()['node_properties']

    source_node_properties = st.selectbox("Source Node Attribute to Match", source_node_properties)

    target_node_properties_response = requests.post(config["neo4j_api"] + "/get_node_properties", json={'node_type':target_node})
    target_node_properties = target_node_properties_response.json()['node_properties']

    target_node_properties = st.selectbox("Target Node Attribute to Match", target_node_properties)

    relationship = st.text_input("Relationship name")

    create_relation = st.button('Create Relation')

    if create_relation:
        relation = {}
        relation['source_node_label'] = source_node
        relation['source_node_attribute_to_match'] = source_node_properties
        relation['target_node_label'] = target_node
        relation['target_node_attribute_to_match'] = target_node_properties
        relation['relation'] = relationship
        relation['relation_properties'] = {'relation':relationship, 'source_node': source_node, 'target_node': target_node}

        response = requests.post(config["neo4j_api"] + "/create_relations", json=relation)
        st.info(response)

################################################
# 👮 Admin
################################################
elif action == "👮 Admin":
    node_types_response = requests.post(config["neo4j_api"] + "/get_nodes")
    node_types = node_types_response.json()['node_types']
    node_attributes = []
    for node in node_types:
        node_properties_response = requests.post(config["neo4j_api"] + "/get_node_properties", json={'node_type':node})
        node_properties = node_properties_response.json()['node_properties']
        node_attributes.append(node_properties)
    nodes_df = pd.DataFrame({'node_type': node_types, 'node_attributes':node_attributes})
    st.title('Nodes in neo4j')
    st.table(nodes_df)

    relation_types_response = requests.post(config["neo4j_api"] + "/get_relations")
    relation_types = relation_types_response.json()

    st.title('Relations in neo4j')
    st.table(relation_types)

    st.header('Delete relation type')
    st.caption("Warning, this will delete ALL relations of relation type in neo4j")
    relation_to_delete = st.selectbox("relation type to delete", relation_types['relation_types'])
    delete_relation = st.button('Delete Relation')

    if delete_relation:
        response = requests.post(config["neo4j_api"] + "/delete_relation", json={'relation_type':relation_to_delete})
        st.info(response)

    st.header('Delete node type')
    st.caption("Warning, this will delete ALL nodes of node type in neo4j")
    node_to_delete = st.selectbox("Node type to delete", node_types)
    delete_node = st.button('Delete Node')

    if delete_node:
        response = requests.post(config["neo4j_api"] + "/delete_node", json={'node_type':node_to_delete})
        st.info(response)

    st.header('Delete all in neo4j')
    st.caption("Warning, this will delete all nodes and relations in neo4j")
    delete_all = st.button('Delete All')

    if delete_all:
        response = requests.post(config["neo4j_api"] + "/delete_all")
        st.info(response)