import collections
import os
from typing import Optional, List, Dict, Union

import yaml
import json
import re
import ast
import pandas as pd
from tqdm import tqdm

from datetime import datetime
import pytz
from neo4j import GraphDatabase
from neo4j.time import DateTime

# Map common python types to neo4j Types
TYPE_MAP =  {
    "int":"Integer",
    "float":"Float",
    "str": "String",
    "bool": "Boolean",
    "datetime": "DateTime",
    "list[int]":"List",
    "list[str]":"List",
    "list[float]": "List",
    "list[double]": "List",
    "dict": "Map",
}

class Neo4jConnection:

    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(
                self.__uri, auth=(self.__user, self.__pwd))
            self.bookmark = self.driver.session().last_bookmark()
        except Exception as e:
            print("Failed to create the driver:", e)

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def query(self, query, parameters=None, db=None):
        assert self.driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.driver.session(
                database=db) if db is not None else self.driver.session()
            response = list(session.run(query, parameters))
        except Exception as e:
            return {"response":f"{e}"}
        finally:
            if session is not None:
                session.close()
        return response

class Neo4jManager():
    def __init__(self):
        self.url = os.environ.get('URL_NEO4J')
        self.username = os.environ.get('USERNAME_NEO4J')
        self.password = os.environ.get('PASSWORD_NEO4J')
        self.neo4j_conn = Neo4jConnection(uri=self.url,
                                          user=self.username,
                                          pwd=self.password)

        
    def create_collection(self, collection_name: str):
        pass

    def delete_collection(self,collection_name: str):
        pass

    def create_index(self, node_index_name: str, node_label: str, node_id: str, db=None):
        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            return session.run("CREATE INDEX {} IF NOT EXISTS FOR (n:{}) ON (n.{})".format(node_index_name, node_label, node_id))

    def merge_node(self, node_labels, node_attributes, db=None):
        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            node_labels = ":".join(node_labels)
            node_attributes = "{"+", ".join([re.sub('[^A-Za-z0-9]+', '_', k)+" : '"+str(node_attributes[k]).replace(
                "'", "").encode("ascii", "ignore").decode()+"'" for k in node_attributes.keys() if not k[0].isdigit()])+"}"
            # print("MERGE (p:{} {}) RETURN p".format(node_label, node_attributes))'
            print("MERGE (p:{} {}) RETURN p".format(node_labels, node_attributes))
            print("\n")
            return session.run("MERGE (p:{} {}) RETURN p".format(node_labels, node_attributes)).single().value()

    def create_node(self, collection_name: str, nodes: List[dict]):
        for node in tqdm(nodes):
            node_attributes = node.copy()
            for key,node_attribute in node_attributes:
                if type(node_attribute) == datetime:
                    neo4j_datetime = DateTime(node_attribute.year, node_attribute.month, node_attribute.day, node_attribute.minute, node_attribute.second)
                    node_attributes.update({key, neo4j_datetime})
            node_labels = [label.capitalize() for label in node['node_labels']]
            node_id = node['node_id']
            node_attributes['neo4j_collection'] = collection_name
            self.merge_node(node_labels,node_attributes)
            for label in node_labels:
                self.create_index(label.lower()+'_index', label, node_id)
    def merge_edge(self, source_node_label, source_node_attribute, target_node_label, target_node_attribute, relation_type, edge_attributes, db=None):

        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            source_attributes = "{"+", ".join([k+" : '"+str(source_node_attribute[k]).replace(
                "'", "").encode("ascii", "ignore").decode()+"'" for k in source_node_attribute.keys()])+"}"
            target_attributes = "{"+", ".join([k+" : '"+str(target_node_attribute[k]).replace(
                "'", "").encode("ascii", "ignore").decode()+"'" for k in target_node_attribute.keys()])+"}"
            edge_attributes = "{"+", ".join(
                [k+" : '"+edge_attributes[k]+"'" for k in edge_attributes.keys()])+"}"
            # .single().value()
            return session.run("MATCH (s:{} {}), (t:{} {}) MERGE (s)<-[e:{} {}]-(t) RETURN e".format(source_node_label, source_attributes, target_node_label, target_attributes, relation_type, edge_attributes))

    def generate_edges(self,collection_name: str, entities_triples: Union[pd.DataFrame,List[dict]], db=None):
        if type(entities_triples) != pd.DataFrame:
            entities_triples = pd.json_normalize(entities_triples, max_level=0)
        for idx, triple in tqdm(entities_triples.iterrows(), total=len(entities_triples)):
            source_node_labels = triple['Subject']['node_labels']
            source_node_attributes = triple['Subject']
            for key,node_attribute in source_node_attributes:
                if type(node_attribute) == datetime:
                    neo4j_datetime = DateTime(node_attribute.year, node_attribute.month, node_attribute.day, node_attribute.minute, node_attribute.second)
                    source_node_attributes.update({key, neo4j_datetime})
            source_node_labels = [label.capitalize() for label in source_node_labels]
            source_node_labels = triple['Subject']['node_labels']

            target_node_attributes = triple['Object']
            for key,node_attribute in target_node_attributes:
                if type(node_attribute) == datetime:
                    neo4j_datetime = DateTime(node_attribute.year, node_attribute.month, node_attribute.day, node_attribute.minute, node_attribute.second)
                    target_node_attributes.update({key, neo4j_datetime})
            target_node_labels = [label.capitalize() for label in target_node_labels]

            relation_type = triple['Predicate']['relation_type']
            relation_type = re.sub('[^A-Za-z0-9]+', '_', relation_type)
            edge_attributes = triple['Predicate']
            for key,edge_attribute in edge_attributes:
                if type(edge_attribute) == datetime:
                    neo4j_datetime = DateTime(edge_attribute.year, edge_attribute.month, edge_attribute.day, edge_attribute.minute, edge_attribute.second)
                    edge_attributes.update({key, neo4j_datetime})
            edge_attributes['neo4j_collection'] = collection_name

            self.merge_edge(source_node_labels, source_node_attributes, target_node_labels,
                    target_node_attributes, relation_type, edge_attributes, db)

    def create_graph(self, collection_name: str, triples: List[dict]):
        triples_df = pd.json_normalize(triples, max_level=0)
        self.create_node(collection_name, triples_df['Subject'].values.tolist())
        self.create_node(collection_name, triples_df['Object'].values.tolist())
        self.generate_edges(collection_name, triples)
        return
    
  
    