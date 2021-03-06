# --------
# Script to mock up an F090W pointsource and fit it.
# ------------

import sys, os
from copy import deepcopy
from functools import partial as argfix
import numpy as np
import matplotlib.pyplot as pl

from forcepho.gaussmodel import Star
from forcepho import paths

from demo_utils import Scene, make_stamp, make_image
from demo_utils import negative_lnlike_stamp, negative_lnlike_nograd
from demo_utils import numerical_image_gradients


def setup_scene(psfname='', size=(100, 100), fudge=1.0, add_noise=False):

    # --- Get a postage stamp ----
    stamp = make_stamp(size, psfname=psfname)

    # --- get the Scene ---
    scene = Scene(galaxy=False)
    sources = [Star()]
    scene.sources = sources

    # --- Get the mock image ----
    label = ['flux', 'x', 'y']
    theta = np.array([100., stamp.nx/2., stamp.ny/2.])
    ptrue = theta * fudge
    stamp.pixel_values = make_image(ptrue, scene, stamp)[0]
    err = stamp.pixel_values.max() * 1e-2
    #err = np.sqrt(stamp.pixel_values.flatten())
    stamp.ierr = np.ones(stamp.npix) / err

    if add_noise:
        noise = np.random.normal(0, err, size=(stamp.nx, stamp.ny))
        stamp.pixel_values += noise
    
    return scene, stamp, ptrue, label


if __name__ == "__main__":

    # --- Get a postage stamp ----
    psfname = os.path.join(paths.psfmixture, 'f090_ng6_em_random.p')
    scene, stamp, ptrue, label = setup_scene(size=(50, 50), psfname=psfname, add_noise=True)    

    nll = argfix(negative_lnlike_stamp, scene=scene, stamp=stamp)
    nll_nograd = argfix(negative_lnlike_nograd, scene=scene, stamp=stamp)    

    # --- Plot a model and gradients thereof ---
    if False:
        theta_init = ptrue * 1.05
        image_init, partials_init = make_image(theta_init, scene, stamp)
        fig, axes = pl.subplots(3, 2, sharex=True, sharey=True)
        ax = axes.flat[0]
        i = ax.imshow(stamp.pixel_values.T, origin='lower')
        ax.text(0.1, 0.9, 'Mock Data', transform=ax.transAxes)
        ax = axes.flat[1]
        i = ax.imshow(image_init.T, origin='lower')
        ax.text(0.1, 0.9, 'Initial Model', transform=ax.transAxes)
        for i, ddtheta in enumerate(partials_init[scene.free_inds, :]):
            ax = axes.flat[i+2]
            ax.imshow(ddtheta.reshape(stamp.nx, stamp.ny).T, origin='lower')
            ax.text(0.1, 0.9, '$\partial I/\partial {}$'.format(label[i]), transform=ax.transAxes)
        pl.show()



    # ---- Test Image Gradients ------
    if True:
        delta = np.ones_like(ptrue) * 1e-6
        #numerical
        grad_num = numerical_image_gradients(ptrue, delta, scene, stamp)
        image, grad = make_image(ptrue, scene, stamp)
        fig, axes = pl.subplots(len(ptrue), 3, sharex=True, sharey=True)
        for i in range(3):
            g = grad[i, :].reshape(stamp.nx, stamp.ny)
            c = axes[i, 0].imshow(grad_num[i,:,:].T, origin='lower')
            fig.colorbar(c, ax=axes[i, 0])
            c = axes[i, 1].imshow(g.T, origin='lower')
            fig.colorbar(c, ax=axes[i, 1])
            c = axes[i, 2].imshow((grad_num[i,:,:] - g).T, origin='lower')
            fig.colorbar(c, ax=axes[i, 2])
        pl.show()

        
    # --- Chi2 on a grid -----
    if False:
        # Needs to be debugged
        mux = np.linspace(47, 53., 100)
        muy = np.linspace(47, 53., 100)
        flux = np.linspace(3000, 5000., 10)
        chi2 = np.zeros([len(mux), len(muy), len(flux)])
    
        for i, x in enumerate(mux):
            for j, y in enumerate(muy):
                for k, f in enumerate(flux):
                    theta = np.array([f, x, y])
                    chi2[i,j,k] = nll(theta)[0]

        sys.exit()


    # ---- Optimization ------

    if True:
        def callback(x):
            #nf += 1
            print(x, nll(x))

        p0 = ptrue.copy() #* 1.04
        p0 *= 1.05
        from scipy.optimize import minimize
        result = minimize(nll, p0, jac=True, bounds=None, callback=callback,
                          options={'ftol': 1e-20, 'gtol': 1e-12, 'factr': 10., 'disp':True, 'iprint': 1, 'maxcor': 20})

        result_nograd = minimize(nll_nograd, p0, jac=False, bounds=None, callback=callback,
                                 options={'ftol': 1e-5, 'gtol': 1e-5, 'factr': 10., 'disp':True, 'iprint': 1, 'maxcor': 20}
                                 )

        resid, partials = make_image(result.x, scene, stamp)
        dim = stamp.pixel_values
        mim = resid
        
        fig, axes = pl.subplots(1, 3, sharex=True, sharey=True, figsize=(13.75, 4.25))
        images = [dim, mim, dim-mim]
        labels = ['Data', 'Model', 'Data-Model']
        for k, ax in enumerate(axes):
            c = ax.imshow(images[k].T, origin='lower')
            pl.colorbar(c, ax=ax)
            ax.set_title(labels[k])

        pl.show()
