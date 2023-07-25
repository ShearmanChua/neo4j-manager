# neo4j-manager

If graph_data folder is not empty, delete all in the folder

```
docker load -i neo4j.tar
docker load -i neo4j-manager.tar
cd build
docker-compose up -d
```

Neo4j commands

# match any nodes where the value of any property contains "No Data"

MATCH (n) WHERE ANY(x IN KEYS(n) WHERE n[x] =~".*No Data") RETURN n, KEYS(n) AS myKeys
