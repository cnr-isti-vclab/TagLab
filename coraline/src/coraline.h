#ifndef CORALINE_H
#define CORALINE_H

#include <vector>
typedef unsigned char uchar;

/* usage:
 expect mask to be black (background) and white (foreground) any other color unknown.

Init Coraline. (rgb pictures)
set thinning radius //optional
 */
class Coraline {
public:
	enum Method { GRAPHCUT, GEODESIC };
	Method method = GRAPHCUT;
	float conservative = 0.2;
	
    uchar *mask = nullptr;
    uchar *img = nullptr;
	double *pred = nullptr;
    std::vector<float> distance;
    std::vector<int> maxima; //for small connected components
    std::vector<int> pixels; //pixels involved in the radius zone.

    std::vector<float> color;
	std::vector<float> foreprob;
	std::vector<float> backprob;
    std::vector<double> forehisto;
    std::vector<double> backhisto;
	
    std::vector<float> foregeo;
    std::vector<float> backgeo;

    double lambda = 0.1; //relative weight of the regional data (from 0 to 1
    double grow = 0.0;
	
    double EPSILON = 0.00000000001;

    int w, h;
    uchar foreground = 2;
    uchar background = 1;
    int radius = 30;
    int q = 16; //color quantization;

	static uchar *rgbToMask(uchar *rgbmask, int w, int h);
	Coraline();
    Coraline(unsigned char *img, unsigned char *mask, int w, int h);
	~Coraline();
	void set(unsigned char *img, int w, int h);
	void setMask(unsigned char *mask, int w, int h);
	void setPred(double *pred, int w, int h);
    uchar *segment();
    uchar *graphCut();
    uchar *geodesic();

    double gradient(int a, int b); //, double color1[3], double color2[3]); //RGB-color information of adjacent pixels

protected:
    void setColorDistribution();

    bool isBorder(int i);
    bool isMax(int i);

    std::vector<int> distanceField(); //return index of pixels in the radius of the border
    void geodesicField(std::vector<float> &probs); //return index of pixels in the radius of the border
};

#endif // CORALINE_H
