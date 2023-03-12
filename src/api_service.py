import ast
import json
import requests
from datetime import date

import pandas as pd
from fastapi import FastAPI, Request
from utils import neo4jManager

app = FastAPI()
neo4j_manager = neo4jManager.Neo4jManager()

@app.get("/")
async def root():
    return {"message": "This is the API service for populating the neo4j Graph Database"}

@app.post("/create_nodes")
async def create_nodes(request: Request):
    '''Create nodes given a List of dictionary of node attributes

        node_collection: the node type of the node to be generated
        nodes: List of nodes attributes in a dictionary
        node_id_field: the key in the node attributes dict that is the node id
        node_labels: any other node types to be tagged to the node

        Example:
        {
            "node_collection" : "Vessel",
            "nodes" : [{"length":"14ft","beam":"2ft","vessel_name":"HMS Prince of Wales"},{"length":"14ft","beam":"2ft","vessel_name":"HMS Repulse"}],
            "node_id_field" : "vessel_name",
            "node_labels" : ["King George V-class battleship","World War II Ship"]
        }
        
    '''
    
    dict_str = await request.json()
    nodes_json = dict_str
    neo4j_manager.create_nodes(node_collection=nodes_json['node_collection'], 
                               nodes=nodes_json['nodes'],
                               node_id_field=nodes_json['node_id_field'],
                               node_labels=nodes_json['node_labels'])

@app.post("/create_relations")
async def create_relations(request: Request):
    '''Create relations between nodes in the neo4j database

            source_node_label: Label of the source node in the relation
            source_node_attribute_to_match: the attribute of the source node to match to the target node on e.g. "product_name"
            target_node_label: Label of the target node in the relation
            target_node_attribute_to_match: the attribute of the target node to match to the source node on e.g. "contains_product"
            relation: name of the relation e.g. "contains_product"
            relation_properties: any relation properties you want to add to the relationship, in a dictionary format
    '''
    dict_str = await request.json()
    relation_json = dict_str

    neo4j_manager.create_relations(source_node_label=relation_json['source_node_label'],
                                   source_node_attribute_to_match=relation_json['source_node_attribute_to_match'],
                                   target_node_label=relation_json['target_node_label'],
                                   target_node_attribute_to_match=relation_json['target_node_attribute_to_match'],
                                   relation=relation_json['relation'],
                                   relation_properties=relation_json['relation_properties'])
    
@app.post("/create_relations_triples")
async def create_relations_triples(request: Request):
    '''Generate relationship edges when provided with either a dataframe or a list of dictionary containing triples
           Properties that are required in the dataframe or dictionary includes:
            Subject: Dictionary of attributes for the Subject node, MUST include "node labels" attribute
            Object: Dictionary of attributes for the Object node, MUST include "node labels" attribute
            Predicate: Dictionary of attributes for the relationship between the nodes, MUST include "relation_type"

           Example:
           {
            "Subject": {"node_labels": ["vessel"], "weight":100tonnes}, 
            "Object": {"node_labels": ["engine"], "engine_name":xxx_engine},
            "Predicate": {"relation_type":"main_engine"}
           }
    '''
    dict_str = await request.json()
    triples_json = dict_str
    df = pd.read_json(triples_json, orient="records")
    df = df.reset_index(drop=True)
    print(df.head())
    print(df.info())

    neo4j_manager.generate_edges_from_triples(entities_triples=df)

@app.get("/get_nodes")
async def get_nodes():
    '''
        Get all node types

        returns a dictionary of node types
        {
            "node_types": [list of node types]
        }
    '''

    node_types = neo4j_manager.list_all_node_types()

    return {"node_types": node_types}

@app.get("/get_relations")
async def get_relations():
    '''
        Get all relation types
        returns a dictionary of relation types
        {
            "relation_types": [list of relation types]
        }
    '''

    relation_types = neo4j_manager.list_all_relation_types()

    return {"relation_types": relation_types}

@app.get("/get_node_properties")
async def get_node_properties(request: Request):
    '''
        Get all node attributes given a node_type
        pass in a request with a json with the node_type

        Example:
        {
            "node_type": "Vessel"
        }

        return {
            "node_properties": [list of node_properties]
        }
    '''
    dict_str = await request.json()
    node_properties = neo4j_manager.list_all_node_properties(dict_str['node_type'])

    return {"node_properties": node_properties}

@app.delete("/delete_all")
async def delete_all():
    '''Delete all nodes and relations in neo4j'''

    neo4j_manager.delete_all()

    return

@app.delete("/delete_node")
async def delete_node(request: Request):
    '''Delete all nodes of node_type in neo4j'''

    dict_str = await request.json()
    neo4j_manager.delete_node(dict_str['node_type'])

    return

@app.delete("/delete_relation")
async def delete_relation(request: Request):
    '''Delete all relations of relation_type in neo4j'''

    dict_str = await request.json()
    neo4j_manager.delete_relation(dict_str['relation_type'])

    return
    