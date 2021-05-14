#include "mutualedges.h"

using namespace std;

float MutualEdges::mutual(vector<float> &histo, int nbins) {
	vector<float> histoA(nbins); //sum of the columns
	vector<float> histoB(nbins); //sum of the rows
	double n = 0.0; //this is the total of the signal!.

	int i = 0;
	for(unsigned int y = 0; y < nbins; y++) {
		float &b = histoB[y];
		for(unsigned int x = 0; x < nbins; x++) {
			int ab = histo[i++];
			histoA[x] += ab;
			b += ab;
		}
		n += b;
	}

	double ILOG2 = 1/log(2.0);
	double m = 0.0;

	for(unsigned int y = 0; y < nbins; y++) {
		float b = histoB[y];
		if(b == 0) continue;
		for(unsigned int x = 0; x < nbins; x++) {
			double ab = histo[x + nbins*y];
			if(ab == 0) continue;
			double a = histoA[x];
			m += ab * log((n*ab)/(a*b))*ILOG2;
		}
	}
	m /= n;

	cout << "M: " << m << endl;
	return float(m);
}

float MutualEdges::hfitness(float ox, float ey) {
	//compute weights and apply to a whole line.
	float start = floor(ey - 2*gaussian);
	float end = ceil(ey + 2*gaussian);
	std::vector<float> weights;
	for(float y = start; y <= end; y++)
		weights.push_back(floor(exp(-pow(y - ey, 2))*(nbins-1)));

	vector<float> histo(nbins*nbins, 0.0);
	for(int x = ox - linewidth/2; x < ox + linewidth/2; x++) {
		for(int y = int(start); y <= int(end); y++) {
			int c = img[x + y*w];
			int g = int(weights[y - int(start)]);
			histo[c + g*nbins]++;
		}
	}
	return mutual(histo, nbins);
}

float MutualEdges::vfitness(float ox, float ey) {
	//compute weights and apply to a whole line.
	double start = floor(ox - 2*gaussian);
	double end = ceil(ox + 2*gaussian);
	std::vector<double> weights;
	for(double x = start; x <= end; x++)
		weights.push_back(floor(exp(-pow(x - ox, 2))*(nbins-1)));

	vector<float> histo(nbins*nbins, 0.0);
	for(int y = ey - linewidth/2; y < ey + linewidth/2; y++) {
		for(int x = int(start); x <= int(end); x++) {
			int c = img[x + y*w];
			int g = int(weights[x - int(start)]);
			histo[c + g*nbins]++;
		}
	}
	return mutual(histo, nbins);
}

void MutualEdges::detect(uint8_t *output) {
	int pad = linewidth + extension;
	float min = 0;
	float max = -1e20;

	for(int i = 0; i < w*h; i++)
		img[i] = floor(img[i]/255.0*nbins);

	vector<float> fitness(h * w, 0);
	for(int y = pad; y < h - pad; y++) {

		for(int x = pad; x < w - pad; x++) {
			cout << int(img[x + y*w]) << " ";
			float vfit = vfitness(x, y);
			float hfit = hfitness(x, y);
			for(int i = -extension; i < extension; i++) {
				fitness[x  + (y+i)*w] = std::max(fitness[x + (y+i)*w], vfit);
				fitness[x + i  + y*w] = std::max(fitness[x + i + y*w], hfit);
			}
			float fit = std::max(vfit, hfit);
			//fitness[x  + y*wall.width()] = fit;
			min = std::min(min, fit);
			max = std::max(max, fit);
		}
		cout << endl;
	}
	cout << "Min max: " << min << " " << max << endl;
	for(size_t i = 0; i < fitness.size(); i++) {
		float f = 255*(fitness[i] - min)/(max - min);
		output[i] = int(floor(f));
	}

/*
	QImage lines(wall.width(), wall.height(), QImage::Format_ARGB32);
	for(int y = 0; y < wall.height(); y++) {
		for(int x = 0; x < wall.width(); x++) {
			int i = x + y*wall.width();
			lines.setPixel(x, y, qRgba(
							  int(floor(fitness[i])),
							  int(floor(fitness[i])),
							  int(floor(fitness[i])),
								  255));
		}
	}

	lines.save(QString("mix_%1_%2_%3_%4.png").arg(linewidth).arg(gaussian).arg(nbins).arg(extension)); */
}

