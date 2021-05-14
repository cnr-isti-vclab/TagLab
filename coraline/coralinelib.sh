#!/bin/bash
cd src
g++ -c -fPIC -std=c++11 -I ./ coralinepy.cpp -o coralinepy.o;
g++ -c -fPIC -std=c++11 -I ./ coraline.cpp -o coraline.o;
g++ -c -fPIC -std=c++11 -I ./ maxflow/graph.cpp -o graph.o;
g++ -c -fPIC -std=c++11 -I ./ mutualedges.cpp -o mutualedges.o;
g++ -shared -Wl,-soname,libcoraline.so -o libcoraline.so  graph.o coraline.o coralinepy.o mutualedges.o
mv libcoraline.so ../
