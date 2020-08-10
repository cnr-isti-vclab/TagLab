#include "coraline.h"
#include "string.h"
#include <iostream>
#include <algorithm>
using namespace std;


#if defined(_WIN32)
  // MS Windows DLLs (*.dll)
#define CORALINE_EXPORT_C __declspec(dllexport)
#else
  // Unix-like Shared Object (.so) operating systems and GCC.
#define CORALINE_EXPORT_C __attribute__ ((visibility ("default")))
#endif 

extern "C" {

	CORALINE_EXPORT_C void Coraline_segment(uchar* img, float *depth, uchar* mask, int w, int h, int *clippoints, int nclips, float lambda = 0.0, float conservative = 1.0, float grow = 0.0, float radius = 30, float depth_weight = 0.0f) {
		Coraline* coraline = new Coraline(img, mask, w, h);
		if(depth)
			coraline->setDepth(depth);
		if(nclips)
			coraline->setClippoints(clippoints, nclips);
		coraline->lambda = lambda;
		coraline->conservative = conservative;
		coraline->grow = grow;
		coraline->radius = radius;
		coraline->img_weight = 1 - depth_weight;
		coraline->depth_weight = depth_weight;

		uchar* segment = coraline->segment();

		memcpy(coraline->mask, segment, (size_t)w * (size_t)h);

		delete[]segment;
		delete coraline;
	}
/*	//Horrible hack since Python truncate pointers.
	Coraline* global = 0;
	double clamp(double v, double lo, double hi) {
		if(v < lo) v = lo;
		if(v > hi) v = hi;
		return v;
	}
	CORALINE_EXPORT_C Coraline* Coraline_new(uchar *img, uchar *mask, int w, int h) {
		
		uchar *tmp = new uchar[w*h*3];
		for(int i = 0; i < w*h; i++)
			tmp[i*3] = tmp[i*3+1] = tmp[i*3+2] = mask[i]*255;
		
		FILE *file = fopen("mask.ppm", "wb");
		fprintf(file, "P6\n%d %d\n255\n", w, h);
		fwrite(tmp, w*h*3, 1, file);
		fclose(file); 
		delete[]tmp;
		
		file = fopen("img.ppm", "wb");
		fprintf(file, "P6\n%d %d\n255\n", w, h);
		fwrite(img, w*h*3, 1, file);
		fclose(file); 
		Coraline *coraline = new Coraline(img, mask, w, h);
		global = coraline;
		cout << "Coraline pointer: " << (void*)coraline << "\n";
		return coraline;
	}
	CORALINE_EXPORT_C void Coraline_delete(Coraline *coraline) {
		if (global != coraline)
			coraline = global;
		delete coraline;
	}
	CORALINE_EXPORT_C void Coraline_setPred(Coraline *coraline, double *pred, int w, int h) {
		if (global != coraline)
			coraline = global;
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
		cout << "Coraline pointer: " << (void*)coraline << "\n";

		coraline->setPred(pred, w, h);
	}
	
	CORALINE_EXPORT_C void Coraline_setLambda(Coraline *coraline, float lambda) {
		if (global != coraline)
			coraline = global;
		cout << "Coraline pointer: " << (void*)coraline << "\n";

		coraline->lambda = lambda;
	}

	CORALINE_EXPORT_C void Coraline_setConservative(Coraline *coraline, float conservative) {
		if (global != coraline)
			coraline = global;
		cout << "Coraline pointer: " << (void*)coraline << "\n";

		coraline->conservative = conservative;
	}
	
	CORALINE_EXPORT_C unsigned char *Coraline_segment(Coraline* coraline) {
		if (global != coraline)
			coraline = global;
		cout << "Coraline pointer: " << (void*)coraline << "\n";


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
		delete []tmp;
		return coraline->mask; 
	}*/
}

/*
g++ -c -fPIC -std=c++11 -I ./ coralinepy.cpp -o coralinepy.o;
g++ -c -fPIC -std=c++11 -I ./ coraline.cpp -o coraline.o;
g++ -c -fPIC -std=c++11 -I ./ maxflow/graph.cpp -o graph.o;
g++ -shared -Wl,-soname,libcoraline.so -o libcoraline.so  graph.o coraline.o coralinepy.o

*/
