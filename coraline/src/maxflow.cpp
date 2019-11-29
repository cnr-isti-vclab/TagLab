/* maxflow.cpp */
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


#include <stdio.h>

#define MAXFLOW_INCLUDE_TEMPLATE_IMPLEMENTATION 1
#include <maxflow.h>

namespace maxflow {
template class Graph<int,int,int>;
template class Graph<short,int,int>;
template class Graph<float,float,float>;
template class Graph<double,double,double>;
}

