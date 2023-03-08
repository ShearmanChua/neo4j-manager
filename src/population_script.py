import json
import requests
import numpy as np
import pandas as pd

def main():

    vessel_ontology = {'Vessel':['Vessel'],'Description':['a ship or large boat']}
    df = pd.DataFrame(vessel_ontology,columns=['Vessel','Description'])

    nodes = {}
    node_labels = ['Vessel']
    nodes['node_collection'] = 'Vessel'
    nodes['node_labels'] = node_labels
    nodes['node_id_field'] = 'Vessel'
    nodes['nodes'] = df.to_dict('records')

    response = requests.post("http://localhost:5050" + "/create_nodes", json=nodes)
    print(response)

    vessel_ontology = {'Coastal_Patrol_Vessel':['Coastal_Patrol_Vessel'],'Description':['A patrol boat (also referred to as a patrol craft, patrol ship, or patrol vessel) is a relatively small naval vessel generally designed for coastal defence, border security, or law enforcement.']}
    df = pd.DataFrame(vessel_ontology,columns=['Coastal_Patrol_Vessel','Description'])

    nodes = {}
    node_labels = ['Coastal_Patrol_Vessel']
    nodes['node_collection'] = 'Coastal_Patrol_Vessel'
    nodes['node_labels'] = node_labels
    nodes['node_id_field'] = 'Coastal_Patrol_Vessel'
    nodes['nodes'] = df.to_dict('records')

    response = requests.post("http://localhost:5050" + "/create_nodes", json=nodes)
    print(response)

    vessel_ontology = {'MMEA_Vessel':['MMEA_Vessel'],'Description':['Vessel generally designed for coastal defence, border security, or law enforcement operated by the Malaysian Maritime Enforcement Agency.']}
    df = pd.DataFrame(vessel_ontology,columns=['MMEA_Vessel','Description'])

    nodes = {}
    node_labels = ['MMEA_Vessel']
    nodes['node_collection'] = 'MMEA_Vessel'
    nodes['node_labels'] = node_labels
    nodes['node_id_field'] = 'MMEA_Vessel'
    nodes['nodes'] = df.to_dict('records')

    response = requests.post("http://localhost:5050" + "/create_nodes", json=nodes)
    print(response)

if __name__ == '__main__':
    main()
