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

    def create_constraint(self, constraint_name: str, node_label: str, node_id: str, db=None):
        '''Create a CONSTRAINT for a node type, so that there are
           no replicated nodes. Requires a name for constraint(lowercase),
           node_label(Uppercase) to be constrained, and the node_id to constraint on'''

        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            return session.run("CREATE CONSTRAINT {} IF NOT EXISTS FOR (n:{}) REQUIRE n.{} IS UNIQUE".format(constraint_name, node_label, node_id))

    def merge_node(self, node_labels: List[str], node_attributes: dict, db=None):
        ''' Create new nodes using th MERGE cypher query
            The MERGE clause ensures that a pattern exists 
            in the graph. Either the entire pattern already exists, 
            or the entire pattern needs to be created. In this way,
            it’s helpful to think of MERGE as attempting a MATCH on 
            the pattern, and if no match is found, a CREATE of the pattern.

            node_labels: a List of strings that define the node types of the node
            node_attributes: attributes for the node being merged'''

        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            node_labels = ":".join(node_labels)
            node_attributes = "{" + ", ".join([re.sub('[^A-Za-z0-9]+', '_', k.lower())+" : '" + str(node_attributes[k]).replace(
                "'", "").encode("ascii", "ignore").decode() + "'" for k in node_attributes.keys() if not k[0].isdigit()]) + "}"

            print("MERGE (n:{} {}) RETURN n".format(node_labels, node_attributes))
            print("\n")

            return session.run("MERGE (n:{} {}) RETURN n".format(node_labels, node_attributes))

    def create_nodes(self, node_collection: str, nodes: List[dict], node_id_field: str, node_labels: List[str] = []):
        '''Create nodes given a List of dictionary of node attributes

           node_collection: the node type of the node to be generated
           nodes: List of nodes attributes in a dictionary
           node_id_field: the key in the node attributes dict that is the node id
           node_labels: any other node types to be tagged to the node'''

        if node_labels:
            node_labels = [label.capitalize() for label in node_labels]
            node_labels.append(node_collection)
            node_labels = list(set(node_labels))
        else:
            node_labels = [node_collection.capitalize()]

        for node in tqdm(nodes):
            node_attributes = node.copy()
            for key,node_attribute in node_attributes.items():
                if isinstance(node_attribute, datetime):
                    neo4j_datetime = DateTime(node_attribute.year, node_attribute.month, node_attribute.day, node_attribute.minute, node_attribute.second)
                    node_attributes.update({key, neo4j_datetime})

            node_id = node[node_id_field]
            node_attributes['node_id'] = node_id

            node_attributes['node_collection'] = node_collection

            self.merge_node(node_labels, node_attributes)

        for label in node_labels:
            self.create_constraint(label.lower(), label, node_id_field)

    def merge_edge(self, source_node_label, source_node_attribute_to_match, target_node_label, target_node_attribute_to_match, relation: str, relation_properties: dict, db=None):
        ''''''

        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            source_node_label = source_node_label.capitalize()
            target_node_label = target_node_label.capitalize()
            source_node_attribute_to_match = source_node_attribute_to_match.lower()
            target_node_attribute_to_match = target_node_attribute_to_match.lower()
            relation = relation.upper()

            edge_attributes = "{" + ", ".join(
                [k.lower() + " : '"+ relation_properties[k]+"'" for k in relation_properties.keys()])+"}"

            # .single().value()
            return session.run("MATCH (s:{}) MATCH(t:{}) WHERE s.{} = t.{} MERGE (s)-[e:{} {}]->(t) RETURN *".format(source_node_label, target_node_label, source_node_attribute_to_match, target_node_attribute_to_match, relation, edge_attributes))
    
    def merge_edge_from_triples(self, source_node_label, source_node_attribute, target_node_label, target_node_attribute, relation_type, edge_attributes, db=None):

        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            source_attributes = "{"+", ".join([k+" : '"+str(source_node_attribute[k]).replace(
                "'", "").encode("ascii", "ignore").decode()+"'" for k in source_node_attribute.keys()])+"}"
            target_attributes = "{"+", ".join([k+" : '"+str(target_node_attribute[k]).replace(
                "'", "").encode("ascii", "ignore").decode()+"'" for k in target_node_attribute.keys()])+"}"
            edge_attributes = "{"+", ".join(
                [k+" : '"+edge_attributes[k]+"'" for k in edge_attributes.keys()])+"}"
            # .single().value()
            return session.run("MATCH (s:{} {}), (t:{} {}) MERGE (s)<-[e:{} {}]-(t) RETURN e".format(source_node_label, source_attributes, target_node_label, target_attributes, relation_type, edge_attributes))

    def generate_edges_from_triples(self, entities_triples: Union[pd.DataFrame,List[dict]], db=None):
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

        if type(entities_triples) != pd.DataFrame:
            entities_triples = pd.json_normalize(entities_triples, max_level=0)

        entities_triples['Subject'] = entities_triples.Subject.apply(lambda x: ast.literal_eval(str(x)))
        entities_triples['Object'] = entities_triples.Object.apply(lambda x: ast.literal_eval(str(x)))

        for idx, triple in tqdm(entities_triples.iterrows(), total=len(entities_triples)):
            source_node_labels = triple['Subject']['node_labels']
            source_node_attributes = triple['Subject']
            for key,node_attribute in source_node_attributes:
                if isinstance(node_attribute, datetime):
                    neo4j_datetime = DateTime(node_attribute.year, node_attribute.month, node_attribute.day, node_attribute.minute, node_attribute.second)
                    source_node_attributes.update({key, neo4j_datetime})
            source_node_labels = [label.capitalize() for label in source_node_labels]

            target_node_labels = triple['Object']['node_labels']
            target_node_attributes = triple['Object']
            for key,node_attribute in target_node_attributes:
                if isinstance(node_attribute, datetime):
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

            self.merge_edge_from_triples(source_node_labels, source_node_attributes, target_node_labels,
                    target_node_attributes, relation_type, edge_attributes, db)
            
    def create_relations(self, source_node_label: str, source_node_attribute_to_match: str, target_node_label: str, target_node_attribute_to_match: str, relation: str, relation_properties: dict, db=None):
        '''Create relations between nodes in the neo4j database

            source_node_label: Label of the source node in the relation
            source_node_attribute_to_match: the attribute of the source node to match to the target node on e.g. "product_name"
            target_node_label: Label of the target node in the relation
            target_node_attribute_to_match: the attribute of the target node to match to the source node on e.g. "contains_product"
            relation: name of the relation e.g. "contains_product"
            relation_properties: any relation properties you want to add to the relationship, in a dictionary format
        '''
        self.merge_edge(source_node_label, source_node_attribute_to_match, target_node_label, target_node_attribute_to_match, relation, relation_properties, db)

    def list_all_node_types(self, db=None):
        ''''''

        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            node_types = session.run("MATCH (n) RETURN distinct labels(n)")
            node_types = [label.value() for label in node_types]
        node_types_expanded = []
        for node_type in node_types:
            node_types_expanded.extend(node_type)
        node_types_expanded = list(dict.fromkeys(node_types_expanded))    

        return node_types_expanded

    def list_all_node_properties(self, node_type: str, db=None):
        ''''''

        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            node_properties = session.run("MATCH (n:{}) RETURN properties(n)".format(node_type))
            node_properties_results = node_properties.value()
            node_properties ={}
            for node in node_properties_results:
                for key,value in node.items():
                    if key not in node_properties:
                        node_properties[key] = value


        node_properties = list(node_properties.keys())
        
        return node_properties

    def delete_all(self, db=None):
        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        return

    def delete_node(self, node_type: str, db=None):
        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            session.run("MATCH (n:{}) DETACH DELETE n".format(node_type))

        return

    def list_all_relation_types(self, db=None):
        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            relation_types = session.run("MATCH ()-[r]->() RETURN TYPE(r)")
            relation_types = [relation.value() for relation in relation_types]
            relation_types = list(dict.fromkeys(relation_types))
        return relation_types

    def delete_relation(self, relation_type:str, db=None):
        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            session.run("MATCH ()-[r:{}]->() DETACH DELETE r".format(relation_type))

    def get_all_triples(self, db=None):
        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            triples = session.run("MATCH (n)-[r]->(n2) RETURN properties(n), properties(r), properties(n2)").data()
            df = pd.DataFrame(triples)
            print(df.info())
        return df.to_dict('records')
    
    def get_page_rank(self, nodeTypes, relationTypes, db=None):
        with self.neo4j_conn.driver.session(database=db) if db is not None else self.neo4j_conn.driver.session() as session:
            nodeTypes = ["'"+node+"'" for node in nodeTypes]
            relationTypes = ["'"+relation+"'" for relation in relationTypes]
            session.run("CALL gds.graph.project('myGraph',[{}],[{}])".format(",".join(nodeTypes),",".join(relationTypes)))
            ranks = session.run("CALL gds.pageRank.stream('myGraph') YIELD nodeId, score RETURN gds.util.asNode(nodeId).node_id AS name, score ORDER BY score DESC, name ASC").data()
            session.run("CALL gds.graph.drop('myGraph') YIELD graphName")
            df = pd.DataFrame(ranks)
            print(df.info())
        return df.to_dict('records')