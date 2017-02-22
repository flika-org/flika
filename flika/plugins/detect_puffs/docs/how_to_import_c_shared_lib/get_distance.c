/*
 
  
  Compilation instructions:
 
 * Windows:
 *  gcc -c get_distance.c
 *  gcc -shared -o get_distance.dll get_distance.o
 */

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

/* Function Declarations */
int getDistance(double *, double *, double *, double *, double *, int);



int getDistance(double *x1, double *y1, double *x2, double *y2, double *dist, int len){
	int i,j;
	double x,y;
	for(i=0;i<len;i++){
		x = x2[i]-x1[i];
		y = y2[i]-y1[i];
		dist[i]=sqrt(x*x+y*y);
	}
}
