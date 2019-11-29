/*****************************************************************************
*    PlanarCut - software to compute MinCut / MaxFlow in a planar graph      *
*                              Version 1.0.1                                 *
*                                                                            *
*    Copyright 2011 - 2012 Eno Töppe <toeppe@in.tum.de>                      *
*                          Frank R. Schmidt <info@frank-r-schmidt.de>        *
******************************************************************************

  If you use this software for research purposes, YOU MUST CITE the following
  paper in any resulting publication:
  
	[1] Efficient Planar Graph Cuts with Applications in Computer Vision.
		F. R. Schmidt, E. Töppe, D. Cremers,
		IEEE CVPR, Miami, Florida, June 2009
		
******************************************************************************

  This software is released under the LGPL license. Details are explained
  in the files 'COPYING' and 'COPYING.LESSER'.
  
*****************************************************************************/

#include "coraline.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <ctime>
#include <string.h>
#include <assert.h>

#include <getopt.h>

using namespace std;



unsigned char *loadSimplePPM(int &w, int &h, const string &filename) {
	
	char line[1000];
	int depth = 0;
	unsigned char *rgb = nullptr;
	long lastpos;
	
	/*  streampos lastpos;
	  ifstream ifs(filename.c_str(), ios_base::binary);*/
	
	FILE *fh = fopen(filename.c_str(), "rb");
	
	w = 0, h = 0;
	
	if (!fgets(line, 1000, fh))
		return nullptr;
	
	if (strcmp(line, "P6\n")) {
		cerr << filename << " is no PPM-Datei\n";
		return nullptr;
	}
	
	while (!feof(fh)) {
		
		lastpos = ftell(fh);
		
		if (!fgets(line, 1000, fh))
			return nullptr;
		
		if (line[0] == '#') {
			//      cout << "Comment: " << line;
		} else if (!w) {
			if (sscanf(line, "%d %d", &w, &h) < 2) {
				cerr << "error while reading the file " << filename;
				cerr << " expected width and height of image\n";
				return nullptr;
			}
		} else if (!depth) {
			if (sscanf(line, "%d", &depth) < 1) {
				cerr << "error while reading the file " << filename;
				cerr << " expected color depth\n";
				return nullptr;
			}
		} else {
			rgb = new unsigned char[w*h*3];
			fseek(fh, lastpos, SEEK_SET);
			if (fread(rgb, 1, w*h*3, fh) != size_t(w*h*3)) {
				fclose(fh);
				return nullptr;
			}
			break;
		}
		
	}
	
	fclose(fh);
	
	return rgb;
	
}


uchar * loadSimplePPMtoMask(int &w, int &h, const string &filename) {
	uchar *tmp = loadSimplePPM(w, h, filename);
	uchar *mask = new uchar[w*h];
	for(int i = 0; i < w*h; i++)
		mask[i] = tmp[i*3]/255;
	delete []tmp;
	return mask;
}


bool saveSimplePPM(unsigned char *rgb, int w, int h, const string &filename) {
	
	ofstream fos(filename.c_str(), ios_base::binary);
	ostringstream ost;
	string s;
	
	if (!fos)
		return false;
	
	fos << "P6" << endl;
	
	ost << w << " " << h << endl;
	
	fos << ost.str();
	fos << "255" << endl;
	
	fos.write((const char*)rgb, w*h*3);
	
	fos.close();
	
	return true;
}


void drawBorder(uchar *rgb, const uchar *mask, int w, int h, uint32_t color) {
	uchar B = ( color     &0xff)/2;
	uchar G = ((color>>8 )&0xff)/2;
	uchar R = ((color>>16)&0xff)/2;
	
	for (int i = 0; i < w*h; i++) {
		uchar &r = rgb[i*3+0];
		uchar &g = rgb[i*3+1];
		uchar &b = rgb[i*3+2];
		
		if(mask[i] == 1 &&
				(mask[i-w-1] == 0 || mask[i-w] == 0 || mask[i-w+1] == 0 ||
				 mask[i-1] == 0 || mask[i-1] == 0 ||
				 mask[i+w-1] == 0 ||mask[i+w] == 0 ||mask[i+w+1] == 0)) {
			r = r/2 + R;
			g = g/2 + G;
			b = b/2 + B;
		}
	}
}

unsigned char *SegMaskAndGreyDataToRGB(uchar *pic, uchar *mask, uchar *omask, uchar *label,
									   int w, int h) {
	
	unsigned char *rgb = new unsigned char[w*h*3];
	int i;
	
	for (i=0; i<w*h; i++) {
		
		int r = (unsigned char)pic[i*3+0];
		int g = (unsigned char)pic[i*3+1];
		int b = (unsigned char)pic[i*3+2];
		
		if(omask[i] == 1 &&
				(omask[i-w-1] == 0 || omask[i-w] == 0 || omask[i-w+1] == 0 ||
				 omask[i-1] == 0 || omask[i-1] == 0 ||
				 omask[i+w-1] == 0 ||omask[i+w] == 0 ||omask[i+w+1] == 0)) {
			rgb[i*3+0] = r/2 + 127;
			rgb[i*3+1] = g/2 + 0;
			rgb[i*3+2] = b/2 + 0;
		} else  if(mask[i] == 1 &&
				   (mask[i-w-1] == 0 || mask[i-w] == 0 || mask[i-w+1] == 0 ||
					mask[i-1] == 0 || mask[i-1] == 0 ||
					mask[i+w-1] == 0 ||mask[i+w] == 0 ||mask[i+w+1] == 0)) {
			rgb[i*3+0] = r/2 + 127;
			rgb[i*3+1] = g/2 + 127;
			rgb[i*3+2] = b/2 + 127;
		}  else  if(label[i] == 1 &&
					(label[i-w-1] == 0 || label[i-w] == 0 || label[i-w+1] == 0 ||
					 label[i-1] == 0 || label[i-1] == 0 ||
					 label[i+w-1] == 0 ||label[i+w] == 0 ||label[i+w+1] == 0)) {
			rgb[i*3+0] = r/2;
			rgb[i*3+1] = g/2 + 127;
			rgb[i*3+2] = b/2;
		} else {
			rgb[i*3+0] = r;
			rgb[i*3+1] = g;
			rgb[i*3+2] = b;
		}
	}
	
	return rgb;
	
}

double diff(int w, int h, uchar *source, uchar *dest) {
	int diff = 0;
	int overlap = 0;
	int intersection = 0;
	for(int i = 0; i < w*h; i++) {
		overlap += source[i] | dest[i];
		diff += source[i]^dest[i];
		intersection += source[i] & dest[i];
	}
	
	return intersection/(double)overlap;
}

void help() {
	cerr << " <coraline> <img> <mask> <label> <output>\n\n"
		 << " -l <float>: lambda weight of foreground prob estimation\n"
		 << " -c <float>: border distrance weight conservative\n";
}

int main(int argc, char *argv[]) {
	
	float lambda = 0.1;
	float conservative = 0.2;
	opterr = 0;
	char c;
	while ((c  = getopt (argc, argv, "hl:c:")) != -1) {
		switch (c)
		{
		case 'h':
			help();
			break;
		case 'l':
			lambda = atof(optarg);
			break;
		case 'c':
			conservative = atof(optarg);
			break;
		}
	}	
	if(optind == argc) {
		cerr << "Too few arguments!\n" << endl;
		help();
		return 1;
	}
	if(optind + 4 < argc) {
		cerr << "Too many arguments!\n" << endl;
		help();
		return 1;
	}
	int w, h;
	
	
	
	size_t pos;
	
	string picname = argv[optind];
	pos = picname.rfind(".ppm");
	
	if (pos == string::npos) {
		cerr << "Coraline only accepts .ppm images\n";
		return -1;
	}
	
	string segname = argv[optind+1];
	pos = segname.rfind(".ppm");
	
	if (pos == string::npos) {
		cerr << "Coraline only accepts .ppm images\n";
		return -1;
	}
	
	string train = argv[optind+2];
	string output = argv[optind+3];
	
	uchar *rgbmask = loadSimplePPM(w, h, segname);
	uchar *rgb = loadSimplePPM(w, h, picname);
	
	
	cout << "Image width: " << w << " and image height " << h << endl;
	
	std::clock_t start = std::clock();
	
	uchar *trainmask = loadSimplePPMtoMask(w, h, train);		
	uchar *oldmask = Coraline::rgbToMask(rgbmask, w, h);
	
	Coraline Coraline(rgb, oldmask, w, h);
	Coraline.radius = 30;
	Coraline.lambda = lambda;
	Coraline.conservative = conservative;
	
	uchar *mask =  Coraline.segment();
	
	double elapsed = ( std::clock() - start ) / (double) CLOCKS_PER_SEC;
	cout<< "Time: " << elapsed <<'\n';
	
	cout << "Diff label to result: " << diff(w, h, oldmask, trainmask) << endl;
	cout << "Diff segm to result: " << diff(w, h, mask, trainmask) << endl;
	
	drawBorder(rgb, mask, w, h, 0xffffff);
	
	unsigned char *ctest = new unsigned char[w*h*3];
	for(int i = 0; i < w*h; i++) {
		ctest[i*3] = ctest[i*3+1] = ctest[i*3+2] = Coraline.foreprob[i]*255;//seg[i]*64;
	}
	saveSimplePPM(ctest, w, h, string("fore.ppm")); 
	
	for(int i = 0; i < w*h; i++) {
		ctest[i*3] = ctest[i*3+1] = ctest[i*3+2] = Coraline.backprob[i]*255;//seg[i]*64;
	}
	saveSimplePPM(ctest, w, h, string("back.ppm")); 
	delete []ctest;
	
	delete []mask;
	
	//caregul
	drawBorder(rgb, oldmask, w, h, 0xff0000);
	drawBorder(rgb, trainmask, w, h, 0x00ff00);
	
	saveSimplePPM(rgb, w, h, string(output));
	
	delete [] rgb;
	delete [] oldmask;
	delete [] rgbmask;
}

