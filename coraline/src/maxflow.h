/*
    Copyright 2006-2015 
    Vladimir Kolmogorov (vnk@ist.ac.at), Yuri Boykov (yuri@csd.uwo.ca) 

    This file is part of MAXFLOW.

    MAXFLOW is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    MAXFLOW is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with MAXFLOW.  If not, see <http://www.gnu.org/licenses/>.
*/


#ifndef maxflow_h
#define maxflow_h

#include <maxflow/block.h>
#include <maxflow/graph.h>


namespace maxflow {
	
typedef Graph<int,int,int> Graph_III;
typedef Graph<short,int,int> Graph_SII;
typedef Graph<float,float,float> Graph_FFF;
typedef Graph<double,double,double> Graph_DDD;

}

// define this if you want to instanciate a graph different from
// the above
#ifdef MAXFLOW_INCLUDE_TEMPLATE_IMPLEMENTATION
#include <maxflow/graph.cpp>
#endif 


#endif 
