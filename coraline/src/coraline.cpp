#include "coraline.h"

#include "maxflow/graph.h"
#include "maxflow/graph.cpp"

#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <math.h>

using namespace std;


bool savePPM(unsigned char *rgb, int w, int h, const string &filename, int channels = 3) {
	
	ofstream fos(filename.c_str(), ios_base::binary);
	ostringstream ost;
	string s;
	
	if (!fos)
		return false;
	
	if(channels == 3)
		fos << "P6\n";
	else
		fos << "P5\n";
	
	ost << w << " " << h << "\n";
	
	fos << ost.str();
	fos << "255\n";

	fos.write((const char*)rgb, w*h*channels);

	fos.close();
	
	return true;
}

uchar *Coraline::rgbToMask(uchar *rgbmask, int w, int h) {
	uchar *mask = new uchar[w*h];
	for(int i = 0; i < w*h; i++) {
		uchar r = rgbmask[i*3+0];
		uchar g = rgbmask[i*3+1];
		uchar b = rgbmask[i*3+2];
		if(r == 0 && g == 0 && b == 0) {
			mask[i] = 0;
		} else if((r == 255 && g == 255 && b == 255) || (r == 213 && g == 165 && b == 0)) {
			mask[i] = 1;
		} else {
			mask[i] = 0;
		}
	}
	return mask;
}

Coraline::Coraline(): img(nullptr), mask(nullptr), w(0), h(1) {}

void Coraline::set(unsigned char *_img, int _w, int _h) {
	img = _img;
	w = _w;
	h = _h;
}
void Coraline::setMask(unsigned char *_mask, int _w, int _h) {
	mask = _mask;
	w = _w;
	h = _h;
}

void Coraline::setDepth(unsigned char *_depth) {
	depth = _depth;
}

void Coraline::setClippoints(int *_clips, int _nclips) {
	clips = _clips;
	nclips = _nclips;
}


void Coraline::setPred(double *_pred, int _w, int _h) {
	pred = _pred;
	assert(_w == w);
	assert(_h == h);

}

Coraline::Coraline(uchar *_img, uchar *_mask, int _w, int _h):
	w(_w), h(_h) {
	//prepare mask
	img = _img;
	mask = _mask;
}

Coraline::~Coraline() {
}

uchar *Coraline::segment() {
	/*unsigned char *test = new unsigned char[w*h*3];
	for(int i = 0; i < w*h; i++) {
		//test[i*3] = test[i*3+1] = test[i*3+2] = distance[i]/radius*255;//seg[i]*64;
		test[i*3] = test[i*3+1] = test[i*3+2] = mask[i]*64;
	}
	savePPM(test, w, h, string("mask.ppm")); */
	
	pixels = distanceField();
	if(lambda > 0.0f)
		setColorDistribution();
	if(method == GEODESIC)
		return geodesic();
	else
		return graphCut();
}

uchar *Coraline::geodesic() {
	//from the distance get the mask (0, 1back 2fore)
	for(int i = 0; i < distance.size(); i++) {
		if(distance[i] < radius)
			mask[i] = 0;
		else mask[i]++;
	}
	
	unsigned char *test = new unsigned char[w*h*3];
	for(int i = 0; i < w*h; i++) {
		//test[i*3] = test[i*3+1] = test[i*3+2] = distance[i]/radius*255;//seg[i]*64;
		test[i*3] = test[i*3+1] = test[i*3+2] = mask[i]*64;
	}
	savePPM(test, w, h, string("maskafter.ppm"));
	
	//run the geodesicField
	geodesicField(color);
	
	for(int i = 0; i < w*h; i++) {
		//test[i*3] = test[i*3+1] = test[i*3+2] = distance[i]/radius*255;//seg[i]*64;
		test[i*3] = test[i*3+1] = test[i*3+2] = foregeo[i]*100;
	}
	savePPM(test, w, h, string("foregeo.ppm"));
	
	for(int i = 0; i < w*h; i++) {
		test[i*3] = test[i*3+1] = test[i*3+2] = backgeo[i]*100;
	}
	savePPM(test, w, h, string("backgeo.ppm"));
	
	//get the mask
	for(int i = 0; i < distance.size(); i++) {
		if(mask[i] == 0) {
			mask[i] = foregeo[i] < backgeo[i]? 1: 0;
		} else mask[i]--;
	}
	return mask;
}

uchar *Coraline::graphCut() {
	//thisis the graphcut

	vector<uchar> dist(distance.size());
	for(int i = 0; i < distance.size(); i++)
		dist[i] = (int)255*(distance[i]/(radius-1));
	savePPM(dist.data(), w, h, "distance.ppm", 1);
	savePPM(depth, w, h, "depth.ppm");
	savePPM(img, w, h, "img.ppm");
	
	typedef maxflow::Graph<double,double,double> GraphType;
	GraphType graph(/*estimated # of nodes*/ (int)sqrt(w*h), /*estimated # of edges*/ 6*(int)sqrt(w*h));
	
	for(int k = 0; k < pixels.size(); k++)
		graph.add_node();
	
	for(int k = 0; k < pixels.size(); k++) {
		int i = pixels[k];
		double wfore = 0.0;
		double wback = 0.0;
		if(distance[i] > radius-1) {
			if(mask[i] == 1)
				wfore = 100000;
			else
				wback = 100000;
		} else {
			if (lambda > 0) {
				wfore = lambda * foreprob[i];
				wback = lambda * backprob[i];
			}
			float signeddistance = distance[i];
			
			if(mask[i] != 1)
				signeddistance *= -1;
			
			double d = signeddistance + grow;
			float distance_penalty = conservative*(d/(radius-1));
			wfore += distance_penalty;
			wback -= distance_penalty;
			/*if(d < 0)

				wback -= distance_penalty;
			else
				wfore -= distance_penalty; */
			
			
			if(pred) {
				if(pred[i] > 0)
					wfore = lambda*pred[i];
				else
					wback = lambda*-pred[i];
			}
		}		
		graph.add_tweights( k, wfore, wback);
	}
	vector<int> indexes(w*h, -1);
	for(int k = 0; k < pixels.size(); k++)
		indexes[pixels[k]] = k;
	
	//for each node look down and right
	int neighbors[4] = { 1, w, w+1, w-1 };
	double neighborsw[4] = { 1.0, 1.0, 1/1.414, 1/1.414 };
	for(int k = 0; k < pixels.size(); k++) {
		int i = pixels[k];
		for(int j = 0; j < 4; j++) {
			int n = i + neighbors[j];
			int kn = indexes[n];
			if(kn >= 0 && kn < pixels.size()) {
				double w = gradient(i, n)*neighborsw[j];
				graph.add_edge(k, kn, w, w);
			}
		}
	}
	
	double flow = graph.maxflow();
	
	uchar *res = new uchar[w*h];
	memcpy(res, mask, w*h);
	
	//printf("Flow = %f\n", flow);
	for(int k = 0; k < pixels.size(); k++) {
		if(graph.what_segment(k) == maxflow::Graph<double, double, double>::SOURCE)
			res[pixels[k]] = 1; //1 foreground, 2 background
		else res[pixels[k]] = 0;
	}
	return res;
}

double Coraline::gradient(int a, int b) { //}, double color1[3], double color2[3]) {
	double diff = 0.0;
	
	for(int i = 0; i < 3; i++)
		diff += pow(((double)img[a*3+ i] - (double)img[b*3+i])/255.0, 2);
	diff = img_weight*sqrt(diff);
	//if(diff < 0.0000001) return EPSILON;

	double depth_diff = 0.0;
	if(depth) {
		depth_diff += depth_weight*3*fabs(((double)depth[a*3] - (double)depth[b*3])/255.0);
	}

	//cout << "depth_weight " << depth_weight << " diff: " << depth_diff << "\n";

	double weight = std::max(EPSILON, exp(-(diff + depth_diff)*25));
	//double weight = std::max(EPSILON, exp(-sqrt(diff)*10));

	return weight;
}


void Coraline::seedBorder(vector<int> &stack) {
	for(int y = 1; y < h-1; y++) {
		for(int x = 1; x < w-1; x++) {
			int i = x + y*w;
			if(isBorder(i)) {
				cout << "x: " << x << "  y: " << y << endl;
				distance[i] = 0.0f;
				stack.push_back(i);
			}
		}
	}
}
void Coraline::seedClips(vector<int> &stack) {
	for(int i = 0; i < nclips; i+= 2) {
		int x = clips[i*2];
		int y = clips[i*2+2];
		int a = x + y*w;
		cout << "x: " << x << "  y: " << y << endl;
		if(distance[a] == 0.0f)
			continue;
		distance[a] =  0;
		stack.push_back(a);
	}
}

vector<int> Coraline::distanceField() {

	distance.resize(w*h, 1e20f);
	
	int kernel[8] = {-1-w, -w, +1-w,  -1, 1,  -1+w,  w, 1+w};
	float filter[8] = {1.41f, 1.0f, 1.41f,  1.0f, 1.0f,  1.41f, 1.0f, 1.41f };
	
	vector<int> stack;
	if(clips)
		seedClips(stack);
	else
		seedBorder(stack);

	//#define HEAP
#ifdef HEAP
	while(stack.size()) {
		int i = stack.front();
		std::pop_heap(stack.begin(), stack.end(), [this](int a, int b) { return this->distance[a] > this->distance[b]; });
		stack.pop_back();
		
		float d = distance[i];
		bool ismax = true;
		for(int k = 0; k < 8; k++) {
			int target = i + kernel[k];
			if(target < 0 || target >= w*h) continue;
			float &orig = distance[target];
			if(d + filter[k] > radius) continue;
			
			if(orig == 1e20f) {
				stack.push_back(target);
				push_heap(stack.begin(), stack.end(), [this](int a, int b) { return this->distance[a] > this->distance[b]; });
			}
			if(d < orig)
				ismax = false;
			
			if(d + filter[k] < orig) {
				orig = d + filter[k];
			}
		}
		if(ismax)
			maxima.push_back(i);
	}
#else
	int start = 0;
	for(int r = 0; r < radius; r++) {
		int end = stack.size();
		for(int k = start; k < stack.size(); k++) {
			int i = stack[k];
			float d = distance[i];
			bool ismax = true;

			
			for(int k = 0; k < 8; k++) {
				int target = i + kernel[k];
				
				int x = target %w;
				int y = (target - x)/w;
				if(x == 0 || y == 0 || x == w-1 || y == h-1)
					continue;
				
				if(target < 0 || target >= w*h) continue;
				float &orig = distance[target];
				if(d + filter[k] > radius) continue;
				
				if(orig == 1e20f)
					stack.push_back(target);
				
				if(d < orig)
					ismax = false;
				
				if(d + filter[k] < orig) {
					orig = d + filter[k];
				}
			}
			if(ismax)
				maxima.push_back(i);
		}
		start = end;
	}
#endif
	maxima.clear();
	for(int i: stack) {
		if(isMax(i))
			maxima.push_back(i);
	}
	for(int i: maxima)
		distance[i] = radius;
	return stack;
}

struct Next {
	int i;
	float d;
	Next(int _i = 0, float _d = 0.0f): i(_i), d(_d) {}
	bool operator<(const Next &a) const {
		return a.d < d;
	}
};

void Coraline::geodesicField(std::vector<float> &probs) {
	int kernel[8] = {-1-w, -w, +1-w,  -1, 1,  -1+w,  w, 1+w};
	float filter[8] = {1.41f, 1.0f, 1.41f,  1.0f, 1.0f,  1.41f, 1.0f, 1.41f };
	
	foregeo.resize(w*h, 1e20f);
	backgeo.resize(w*h, 1e20f);
	
	vector<Next> stack;
	
	for(int y = 1; y < h-1; y++) {
		for(int x = 1; x < w-1; x++) {
			int i = x + y*w;
			if(isBorder(i)) {
				if(mask[i] == 2) {
					foregeo[i] = 0.0f;
					stack.push_back(Next(i, 0.0f));
				}
				if(mask[i] == 1 ) {
					backgeo[i] = 0.0f;
					stack.push_back(Next(i, 0.0f));
				}
			}
		}
	}
	
	make_heap(stack.begin(), stack.end()); //not needed it's all zero distances...
	
	while(stack.size()) {
		Next next = stack.front();
		int i = next.i;
		std::pop_heap(stack.begin(), stack.end());
		stack.pop_back();
		
		float fd = foregeo[i];
		float bd = backgeo[i];
		
		if(fd < bd) { //updating foreground
			if(fd < next.d) continue; //already visited.
			assert(fd < 1e10);
			for(int k = 0; k < 8; k++) {
				
				int target = i + kernel[k];
				if(mask[target] != 0) continue;
				
				if(target < 0 || target >= w*h) continue;
				float &foreorig = foregeo[target];
				float &backorig = backgeo[target];
				
				float w = fabs(probs[i] - probs[target]);
				float dist = fd + filter[k]*w;
				
				
				if(backorig < dist) continue;
				
				if(dist < foreorig) {
					stack.push_back(Next(target, dist));
					push_heap(stack.begin(), stack.end());
					foreorig = dist;
				}
				
			}
		}  else {
			for(int k = 0; k < 8; k++) {
				int target = i + kernel[k];
				if(mask[target] != 0) continue;
				
				if(target < 0 || target >= w*h) continue;
				float &foreorig = foregeo[target];
				float &backorig = backgeo[target];
				
				float w = fabs(probs[i] - probs[target]);
				float dist = bd + filter[k]*w;
				
				if(foreorig < dist) continue;
				
				if(dist < backorig) {
					stack.push_back(Next(target, dist));
					push_heap(stack.begin(), stack.end());
					backorig = dist;
				}
			}
		}
	}
	/*   int start = 0;
	for(int r = 0; r < radius; r++) {
		int end = forestack.size();
		for(int k = start; k < forestack.size(); k++) {
			int i = forestack[k];
			float d = foregeo[i];
			bool ismax = true;
			for(int k = 0; k < 8; k++) {
				int target = i + kernel[k];
				if(target < 0 || target >= w*h) continue;
				float &orig = foregeo[target];
				if(d + filter[k] > radius) continue;
				
				if(orig == 1e20f)
					forestack.push_back(target);
					
				if(d < orig)
					ismax = false;
					
				if(d + filter[k] < orig) {
					orig = d + filter[k];
				 }
			 }
			if(ismax)
				maxima.push_back(i);
		}
		start = end;
	}
	for(int i: maxima)
		distance[i] = radius;
	return stack; */
}


bool Coraline::isBorder(int i) {
	uchar p = mask[i];
	int kernel[8] = {-1-w, -w, +1-w, -1, 1, -1+w, w, 1+w};
	for(int k = 0; k < 8; k++) {
		if(p != mask[i+kernel[k]])
			return true;
	}
	return false;
}

bool Coraline::isMax(int i) {
	uchar p = mask[i];
	int kernel[8] = {-1-w, -w, +1-w, -1, 1, -1+w, w, 1+w};
	float d = distance[i];
	for(int k = 0; k < 8; k++) {
		if(d < distance[i+kernel[k]])
			return false;
	}
	return true;
}

void Coraline::setColorDistribution() {
	int depth = 256/q;
	forehisto.resize(depth*depth*depth, 0);
	backhisto.resize(depth*depth*depth, 0);
	
	color.resize(w*h);
	
	double totfore = 0;
	double totback = 0;
	//for(int i: pixels) {
	//   assert(distance[i] <= radius);
	for(int i = 0; i < w*h; i++) {
		if(distance[i] < radius) continue;
		int r = img[i*3+0]/q;
		int g = img[i*3+1]/q;
		int b = img[i*3+2]/q;
		
		double w = distance[i]/(double)radius;
		w = 1.0;
		if(mask[i] == 1) {
			forehisto[r + g*depth + b*depth*depth] += w;
			totfore += w;
		} else {
			backhisto[r + g*depth + b*depth*depth] += w;
			totback += w;
		}
	}
	double max = 0;
	for(int i = 0; i < forehisto.size(); i++) {
		//if(forehisto[i] != 0 || backhisto[i] != 0)
		//forehisto[i] /= totfore;
		//backhisto[i] /= totback;
		max = std::max(forehisto[i], max);
		max = std::max(backhisto[i], max);
	}
	foreprob.resize(w*h, 0.5);
	backprob.resize(w*h, 0.5);
	int threshold = 50;
	for(int i = 0; i < w*h; i++) {
		int r = img[i*3+0]/q;
		int g = img[i*3+1]/q;
		int b = img[i*3+2]/q;
		int k = r + g*depth + b*depth*depth;
		
		//if(forehisto[k] > 0.01)
		//	foreprob[i] = 1;
		//else
		//	foreprob[i] = 0;
		if(backhisto[k] < threshold && forehisto[k] < threshold)
			continue;
		
		if(backhisto[k] < threshold) {
			foreprob[i] = 100.0;
			backprob[i] = 0.0;
		} else if(forehisto[k] < threshold) {
			foreprob[i] = 0.0;
			backprob[i] = 100.0;
		} else {
			//foreprob[i] = (forehisto[k]/totfore)/((forehisto[k]/totfore) + (backhisto[k]/totfore));
			//backprob[i] = 1 - foreprob[i];
		}
		
		
		
		//foreprob[i] = forehisto[k]/(forehisto[k] + backhisto[k]);
		//backprob[i] = backhisto[k]/(forehisto[k] + backhisto[k]);

		
		//if(method == GEODESIC)
			//color[i] = lambda*(forehisto[k] - backhisto[k])/(float)(max); //from -1 to 1
			//foreprob[i] = color[i] > 0? color[i]: 0;
			//backprob[i] = color[i] < 0? -color[i]: 0;
			
			//foreprob[i] / 4;
			//backprob[i] / 4;
		//else
			//color[i] = 1.0/(1.0 + exp(-color[i]*25));
	}
	cout << endl;
}


int tohisto(double c[3], int depth, int q) {
	int r = ((int)c[0])/q;
	int g = ((int)c[1])/q;
	int b = ((int)c[2])/q;
	return r + g*depth + b*depth*depth;
}

void toYCaCb(double c[3], double *y) {
	y[0] =       0.299   * c[0] + 0.587   * c[1] + 0.114   * c[2];
	y[1] = 0.5 - 0.16874 * c[0] - 0.33126 * c[1] + 0.5     * c[2];
	y[2] = 0.5 + 0.50000 * c[0] - 0.41869 * c[1] - 0.08131 * c[2];
}











int count(int n) {
	int count = 0;
	for(int i = 0; i < 8; i++)
		if(n & 1<<i)
			count++;
	return count;
}

int neighbours(unsigned char *mask, int pos, int w, unsigned char fore) {
	int n = 0;
	if(mask[pos-1] == fore) n += 1;   //p2 w
	if(mask[pos+w-1] == fore) n += 2;
	if(mask[pos+w] == fore) n += 4;   //p4 n
	if(mask[pos+w+1] == fore) n += 8;
	if(mask[pos+1] == fore) n += 16;  //p6 e
	if(mask[pos+1-w] == fore) n += 32;
	if(mask[pos-w] == fore) n += 64;  //p8 s
	if(mask[pos-1-w] == fore) n += 128;
	return n;
}

//replaces foreground with 0 when thinning
void thin(unsigned char *mask, int w, int h, unsigned char foreground, int radius) {
	
	vector<int> changes;
	for(int iter = 0; iter < radius; iter++) {
		//1 get the neighbors
		changes.clear();
		for(int y = 1; y < h-1; y++) {
			for(int x = 1; x < w-1; x++) {
				int pos = x + y*w;
				if(mask[pos] != foreground)
					continue;
				int n = neighbours(mask, pos, w, foreground);
				if(n == 255) continue;
				int c = count(n);
				if(c < 2 || c > 6) continue;
				if((n & (1 + 4 + 16)) != 21 && (n & (4 + 16 + 64)) != 84) //w n e  and  n e s (s and w)
					changes.push_back(pos);
			}
		}
		for(int i: changes)
			mask[i] = 0;
		
		changes.clear();
		for(int y = 1; y < h-1; y++) {
			for(int x = 1; x < w-1; x++) {
				int pos = x + y*w;
				if(mask[pos] != foreground)
					continue;
				int n = neighbours(mask, pos, w, foreground);
				if(n == 255 || n == 0) continue;
				
				int c = count(n);
				if(c < 2 || c > 6) continue;
				if((n & (1 + 4 + 64)) != 69 && (n & (1 + 16 + 64) != 81))  // w n s   w e s (e and n)<
					changes.push_back(pos);
			}
		}
		
		for(int i: changes)
			mask[i] = 0;
	}
}
