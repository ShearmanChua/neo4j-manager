import json
import requests
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_agraph.config import Config, ConfigBuilder

from utils import neo4jManager
from utils import utils

config = utils.load_config()
st.sidebar.title(config["sidebar_title"])

# sidebar dropdown selection
action = st.sidebar.selectbox(
    "Select action", ("💽 Load data", "📈 Node Population", "🔀 Relation Population", "👮 Admin", "🔭 Visualize")
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
    node_types_response = requests.get(config["neo4j_api"] + "/get_nodes")
    node_types = node_types_response.json()['node_types']

    st.write('Nodes in neo4j DB: {}'.format(node_types))

    source_node = st.selectbox("Source Node", node_types)
    target_node = st.selectbox("target Node", node_types)

    source_node_properties_response = requests.get(config["neo4j_api"] + "/get_node_properties", json={'node_type':source_node})
    source_node_properties = source_node_properties_response.json()['node_properties']

    source_node_properties = st.selectbox("Source Node Attribute to Match", source_node_properties)

    target_node_properties_response = requests.get(config["neo4j_api"] + "/get_node_properties", json={'node_type':target_node})
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
    node_types_response = requests.get(config["neo4j_api"] + "/get_nodes")
    node_types = node_types_response.json()['node_types']
    node_attributes = []
    for node in node_types:
        node_properties_response = requests.get(config["neo4j_api"] + "/get_node_properties", json={'node_type':node})
        node_properties = node_properties_response.json()['node_properties']
        node_attributes.append(node_properties)
    nodes_df = pd.DataFrame({'node_type': node_types, 'node_attributes':node_attributes})
    st.title('Nodes in neo4j')
    st.table(nodes_df)

    relation_types_response = requests.get(config["neo4j_api"] + "/get_relations")
    relation_types = relation_types_response.json()

    st.title('Relations in neo4j')
    st.table(relation_types)

    st.header('Delete relation type')
    st.caption("Warning, this will delete ALL relations of relation type in neo4j")
    relation_to_delete = st.selectbox("relation type to delete", relation_types['relation_types'])
    delete_relation = st.button('Delete Relation')

    if delete_relation:
        response = requests.delete(config["neo4j_api"] + "/delete_relation", json={'relation_type':relation_to_delete})
        st.info(response)

    st.header('Delete node type')
    st.caption("Warning, this will delete ALL nodes of node type in neo4j")
    node_to_delete = st.selectbox("Node type to delete", node_types)
    delete_node = st.button('Delete Node')

    if delete_node:
        response = requests.delete(config["neo4j_api"] + "/delete_node", json={'node_type':node_to_delete})
        st.info(response)

    st.header('Delete all in neo4j')
    st.caption("Warning, this will delete all nodes and relations in neo4j")
    delete_all = st.button('Delete All')

    if delete_all:
        response = requests.delete(config["neo4j_api"] + "/delete_all")
        st.info(response)
###############################################
# 🔭 Visualize
################################################

if action == "🔭 Visualize":

    triples = requests.get(config["neo4j_api"] + "/get_all_triples")
    triples_list = triples.json()['triples']
    df = pd.DataFrame.from_records(triples_list)

    nodes = []
    edges = []
    node_ids = []

    for idx, row in df.iterrows():
        sub = row['properties(n)']
        rel = row['properties(r)']
        obj = row['properties(n2)']
        if sub['node_id'] not in node_ids:
            nodes.append( Node(id=sub['node_id'], 
                            label=sub['node_id'], 
                            title = json.dumps(sub),
                            size=25, 
                            shape="circularImage",
                            image= sub['image'] if 'image' in sub.keys() else "") 
                        ) # includes **kwargs
            node_ids.append(sub['node_id'])
        if obj['node_id'] not in node_ids:
            nodes.append( Node(id=obj['node_id'], 
                            label=obj['node_id'], 
                            title = json.dumps(obj),
                            size=25,
                            shape="circularImage",
                            image=obj['image'] if 'image' in obj.keys() else "") 
                        )
            node_ids.append(obj['node_id'])
        edges.append( Edge(source=sub['node_id'], 
                        label=rel["relation"], 
                        target=obj['node_id'], 
                        # **kwargs
                        ) 
                    ) 
    
    # 1. Build the config (with sidebar to play with options) .
    config_builder = ConfigBuilder(nodes)
    graph_config = config_builder.build()

    # config = Config(width=750,
    #                 height=950,
    #                 directed=True, 
    #                 physics=True, 
    #                 hierarchical=False,
    #                 # **kwargs
    #                 )

    return_value = agraph(nodes=nodes, 
                        edges=edges, 
                        config=graph_config)
    
    node_types_response = requests.get(config["neo4j_api"] + "/get_nodes")
    node_types = node_types_response.json()['node_types']
    nodes_to_rank = st.multiselect(
                                    'What nodes to rank',
                                    node_types)

    relation_types_response = requests.get(config["neo4j_api"] + "/get_relations")
    relation_types = relation_types_response.json()["relation_types"]

    relations_to_rank = st.multiselect(
                                    'What relations to rank',
                                    relation_types)
    
    generate_rank = st.button('Generate Ranking')
    
    if generate_rank:
    
        ranking = requests.get(config["neo4j_api"] + "/get_page_rank", json={'node_type':nodes_to_rank,'relation_type':relations_to_rank})
        ranking_list = ranking.json()['ranking']
        rank_df = pd.DataFrame.from_records(ranking_list)
        st.header("Critical Nodes by Rank")
        st.dataframe(rank_df)