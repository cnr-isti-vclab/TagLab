#ifndef MUTUALEDGES_H
#define MUTUALEDGES_H

#include <cstdint>
#include <vector>
#include <iostream>

#include <math.h>
class MutualEdges {
public:
	MutualEdges() {}

	double gaussian = 1; //line smoothing when convoluting.
	double linewidth = 30;
	int nbins = 16;
	int extension = 1;
	uint8_t *img = nullptr;
	uint32_t w = 0;
	uint32_t h = 0;

	float mutual(std::vector<float> &histo, int nbins);
	float hfitness(float ox, float ey);
	float vfitness(float ox, float ey);
	void detect(uint8_t *output);

};


#endif // MUTUALEDGES_H
