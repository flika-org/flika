import global_vars as g

import numpy as np
def extractV(movie, Vin):
	'''
	Translated, by Brett Settle from MATLAB program in "Optical recording of action potentials in 
	mammalian neurons using a microbial rhodopsin", algorithm credit to Adam E.
	Cohen 22 Jan 2011

	For ParkerLab, UCI Dept of Neurobiology and Behavioral Science, 1146 McGaugh Hall

	Identifies and weights voltage-responsive pixels in a movie of a cell
	expressing a voltage indicating fluorescent protein.  Constructs an
	estimate of the membrane potential from a weighted sum of the intensities
	of each pixel in each frame of the movie.


	Input:
	movie: [K N M] array (inverse from MATLAB) K frame M by N movie
	Vin: K length array with measured membrane potential at each frame.
	In the absence of electrical recording, Vin can be replaced by
	the whole-cell fluorescence.

	Output:
	Vout: K by 1 vector of estimated membrane voltages.  Vout is the
	least-square estimate, assuming the model above.
	corrimg: Image showing correlation between Vin and signal at each pixel.
	This image alone is insufficient to determine the weight matrix because
	it does not take into account the level of noise at each pixel.
	weightimg: Weighting coefficients assigned to each pixel, based on
	correlation with Vin and residual noise.
	offsetimg: Offset to be added to each pixel to produce a Vout with the
	correct offset.

	'''
	average_frame = np.average(movie, 0)
	average_voltage = np.average(Vin)
	dV = Vin - average_voltage
	L = len(Vin)

	movie = movie - average_frame

	y, x = np.shape(average_frame)

	dV2 = np.reshape(dV, (L, 1, 1))
	corrimg = np.average(movie * dV2, 0)
	corrimg /= np.mean(dV ** 2)

	movie2 = movie / corrimg

	sigmaimg = np.mean((movie2 - dV2) ** 2, 0)

	weight_movie = 1 / sigmaimg
	weight_movie /= np.mean(weight_movie)

	dVout = np.squeeze(np.mean(movie2 * weight_movie, (2, 1)))

	Vout = dVout + average_voltage
	offsetimg = average_frame - average_voltage * corrimg
	return Vout, corrimg, weight_movie, offsetimg

def ApplyWeights(movie, corrimg, weightimg, offsetimg):
	'''
	second part of algorithm listed above
	Apply a correlation image (M by N), weight image (M by N) and offset 
	image (M by N) to a movie (M by N by K), to produce an estimated voltage 
	Vout (K by 1).

	takes output from extractV, generates estimate of membrane potential.

	Adam E. Cohen 22 Jan 2011

	'''
	mt, my, mx = np.shape(movie)
	movie -= offsetimg
	scalemat = weightimg / corrimg
	Vout = np.squeeze(np.mean(movie * scalemat, (2, 1)))
	return Vout