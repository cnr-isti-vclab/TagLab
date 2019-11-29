#include "coraline.h"
#include "string.h"
#include <iostream>
#include <algorithm>
using namespace std;

extern "C" {
	double clamp(double v, double lo, double hi) {
		if(v < lo) v = lo;
		if(v > hi) v = hi;
		return v;
	}
	Coraline* Coraline_new(uchar *img, uchar *mask, int w, int h) {
		
		uchar *tmp = new uchar[w*h*3];
		for(int i = 0; i < w*h; i++)
			tmp[i*3] = tmp[i*3+1] = tmp[i*3+2] = mask[i]*255;
		
		FILE *file = fopen("mask.ppm", "wb");
		fprintf(file, "P6\n%d %d\n255\n", w, h);
		fwrite(tmp, w*h*3, 1, file);
		fclose(file); 
		
		file = fopen("img.ppm", "wb");
		fprintf(file, "P6\n%d %d\n255\n", w, h);
		fwrite(img, w*h*3, 1, file);
		fclose(file); 
		
		return new Coraline(img, mask, w, h);
	}
	void Coraline_delete(Coraline *coraline) {
		delete coraline;
	}
	void Coraline_setPred(Coraline *coraline, double *pred, int w, int h) {
		
		vector<uchar> img(w*h*3);
		for(int i = 0; i < w*h; i++) {
			pred[i] -= 0.8;
			pred[i] = clamp(pred[i] + 1, 0.0, 2.0)/2.0;
			img[i*3+0] = img[i*3+1] = img[i*3+2] = 255.0*pred[i];
		}
		FILE *file = fopen("pred.ppm", "wb");
		fprintf(file, "P6\n%d %d\n255\n", w, h);
		fwrite(img.data(), w*h*3, 1, file);
		fclose(file); 
		
		coraline->setPred(pred, w, h);
	}
	
	void Coraline_setLambda(Coraline *coraline, float lambda) {
		coraline->lambda = lambda;
	}
	void Coraline_setConservative(Coraline *coraline, float conservative) {
		coraline->conservative = conservative;
	}
	
	unsigned char *Coraline_segment(Coraline* coraline) { 
		int w = coraline->w;
		int h = coraline->h;
		
		uchar *segment = coraline->segment();
		memcpy(coraline->mask, segment, w*h);
		
		uchar *tmp = new uchar[w*h*3];
		for(int i = 0; i < w*h; i++)
			tmp[i*3] = tmp[i*3+1] = tmp[i*3+2] = segment[i]*255;
		
		FILE *file = fopen("result.ppm", "wb");
		fprintf(file, "P6\n%d %d\n255\n", w, h);
		fwrite(tmp, w*h*3, 1, file);
		
		fclose(file); 
		return coraline->mask; 
	}
}

/*
g++ -c -fPIC -std=c++11 -I ./ coralinepy.cpp -o coralinepy.o;
g++ -c -fPIC -std=c++11 -I ./ coraline.cpp -o coraline.o;
g++ -c -fPIC -std=c++11 -I ./ maxflow/graph.cpp -o graph.o;
g++ -shared -Wl,-soname,libcoraline.so -o libcoraline.so  graph.o coraline.o coralinepy.o

*/
