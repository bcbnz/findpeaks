# ----------------------------------------------------
# Name        : findpeaks.py
# Author      : E.Taskesen
# Contact     : erdogant@gmail.com
# github      : https://github.com/erdogant/findpeaks
# Licence     : MIT
# ----------------------------------------------------
from findpeaks.utils.smoothline import smooth_line1d
import findpeaks.utils.imagepers as imagepers
from peakdetect import peakdetect
from scipy.ndimage.filters import maximum_filter
from scipy.ndimage.morphology import generate_binary_structure, binary_erosion
from scipy import misc
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd
import numpy as np
import wget
import os
from tqdm import tqdm
import cv2 # Only for 2D images required

def fit(X, xs=None, lookahead=200, smooth=None, mask=0, resize=None, scale=True, togray=False, denoise=10, verbose=3):
    """Detection of peaks and valleys in a 1D vector.

    Parameters 1D
    -------------
    X : array-like 1D vector
        Input data.
    lookahead : int, (default : 200)
        Looking ahead for peaks. For very small 1d arrays, lets say up to 50 datapoints, set low numbers such as 1 or 2.
    smooth : int, (default : 10)
        Smoothing factor by interpolation. The higher the number, the more smoothing will occur.

    Parameters 2D-array
    -------------------
    X : array-like RGB or 2D-array
        Input image data.
    mask : float, (default : 0)
        Values <= mask are set as background.
    scale : bool, (default : False)
        Scaling in range [0-255] by img*(255/max(img))
    denoise : int, (default : 10 or None to disable)
        Denoising image, where the first value is the  filter strength. Higher value removes noise better, but removes details of image also.
    togray : bool, (default : False)
        Conversion to gray scale.
    resize : tuple, (default : None)
        Resize to desired (width,length).
        
    Returns
    -------
    dict.
    labx : array-like
        Labels of the detected distributions.
    max_peaks : list
        Detected peaks with maximum.
    min_peaks : list
        Detected peaks with minimum.

    Examples
    --------
    >>> import findpeaks
    >>> X = [9,60,377,985,1153,672,501,1068,1110,574,135,23,3,47,252,812,1182,741,263,33]
    >>> out = findpeaks.fit(X, lookahead=2)
    >>> findpeaks.plot(out)
    >>>
    >>> # Image example
    >>> f = 'image.png'
    >>> img = cv2.imread(f)
    >>> img = cv2.resize(img, (200, 200))


    """
    # Check datatype
    if isinstance(X, list):
        X=np.array(X)
    if isinstance(X, type(pd.DataFrame())):
        X=X.values

    if len(X.shape)>1:
        if verbose>=3: print('[findpeaks] >2D array is detected, finding 2d peaks..')
        out = peaks2d(X, mask=mask, scale=scale, denoise=denoise, togray=togray, resize=resize, verbose=verbose)
    else:
        if verbose>=3: print('[findpeaks] >1D array is detected, finding 1d peaks..')
        out = peaks1d(X, xs=xs, lookahead=lookahead, smooth=smooth, verbose=verbose)

    return(out)


# %%
def peaks1d(X, xs=None, lookahead=200, smooth=None, verbose=3):
    # Here we extend the data by factor 3 interpolation and then we can nicely smoothen the data.
    Xo = X.copy()
    out = {}
    out['Xorig'] = Xo
    if smooth:
        X = smooth_line1d(X, nboost=len(X)*smooth, method=2, showfig=False)

    # Peak detect
    [max_peaks, min_peaks] = peakdetect(np.array(X), lookahead=lookahead)

    # Check
    if min_peaks==[] or max_peaks==[]:
        if verbose>=3: print('[findpeaks] >No peaks detected. Tip: try lowering lookahead value.')
        return(None)

    idx_peaks, _ = zip(*max_peaks)
    idx_peaks = np.array(list(idx_peaks))
    idx_valleys, _ = zip(*min_peaks)
    idx_valleys = np.append(np.array(list(idx_valleys)), len(X) - 1)
    idx_valleys = np.append(0, idx_valleys)

    # Group distribution
    labx_s = np.zeros((len(X))) * np.nan
    for i in range(0, len(idx_valleys)-1):
        labx_s[idx_valleys[i]:idx_valleys[i+1]+1] = i + 1

    if smooth:
        # Scale back to original data
        min_peaks = np.minimum(np.ceil(((idx_valleys/len(X))*len(Xo))).astype(int), len(Xo) - 1)
        max_peaks =  np.minimum(np.ceil(((idx_peaks/len(X))*len(Xo))).astype(int), len(Xo) - 1)
        # Scaling is not accurate for indexing and therefore, a second wave of searching for peaks
        max_peaks_corr = []
        for max_peak in max_peaks:
            getrange=np.arange(np.maximum(max_peak-lookahead,0),np.minimum(max_peak+lookahead,len(Xo)))
            max_peaks_corr.append(getrange[np.argmax(Xo[getrange])])
        # Scaling is not accurate for indexing and therefore, a second wave of searching for peaks
        min_peaks_corr = []
        for min_peak in min_peaks:
            getrange=np.arange(np.maximum(min_peak-lookahead,0),np.minimum(min_peak+lookahead,len(Xo)))
            min_peaks_corr.append(getrange[np.argmin(Xo[getrange])])
        # Set the labels
        labx = np.zeros((len(Xo))) * np.nan
        for i in range(0, len(min_peaks)-1):
            labx[min_peaks[i]:min_peaks[i+1]+1] = i + 1

        # Store based on original locations
        out['labx'] = labx
        out['xs'] = np.arange(0,len(Xo))
        out['min_peaks'] = np.c_[min_peaks_corr, Xo[min_peaks_corr]]
        out['max_peaks'] = np.c_[max_peaks_corr, Xo[max_peaks_corr]]

    # Store
    if xs is None: xs = np.arange(0,len(X))

    out['method'] = 'peaks1d'
    out['labx_s'] = labx_s
    out['min_peaks_s'] = np.c_[idx_valleys, X[idx_valleys]]
    out['max_peaks_s'] = np.c_[idx_peaks, X[idx_peaks]]
    out['X_s'] = X
    out['xs_s'] = xs

    return(out)

# %%
def peaks2d(X, mask=0, scale=True, denoise=10, togray=False, resize=None, verbose=3):
    # Preprocessing the iamge
    Xproc = preprocessing(X, mask=mask, scale=scale, denoise=denoise, togray=togray, resize=resize, showfig=False, verbose=verbose)
    # Compute mesh-grid and persistance
    g0, xx, yy = _compute_with_topology(Xproc)
    # Compute peaks using local maximum filter.
    Xmask = _compute_with_mask(Xproc, mask=mask)

    # Store
    results = {}
    results['Xorig'] = X
    results['Xproc'] = Xproc
    results['Xmask'] = Xmask
    results['g0'] = g0
    results['xx'] = xx
    results['yy'] = yy
    results['args'] = {}
    results['args']['mask']=mask
    results['args']['scale']=scale
    results['args']['denoise']=denoise
    results['args']['togray']=togray
    results['args']['resize']=resize
    results['method'] = 'peaks2d'
    # Return
    if verbose>=3: print('[findpeaks] >Fin.')
    return results

# %%
def preprocessing(X, mask=0, scale=True, denoise=10, togray=False, resize=None, showfig=False, verbose=3):
    # Resize
    if resize:
        X = _resize(X, resize=resize)
        if showfig:
            plt.figure()
            plt.imshow(X)
    # Scaling
    if scale:
        X = _scale(X, verbose=verbose)
        if showfig:
            plt.figure()
            plt.imshow(X)
    # Convert to gray image
    if togray:
        X = _togray(X, verbose=verbose)
        if showfig:
            plt.figure()
            plt.imshow(X, cmap='gray' if togray else None)
    # Denoising
    if denoise is not None:
        X = _denoise(X, h=denoise, verbose=verbose)
        if showfig:
            plt.figure()
            plt.imshow(X, cmap='gray' if togray else None)
    # Return
    return X


# %%
def _scale(X, verbose=3):
    if verbose>=3: print('[findpeaks] >Scaling image between [0-255] and to uint8')
    try:
        X = X * (255 / np.max(X))
        # Downscale typing
        X = np.uint8(X)
    except:
        if verbose>=2: print('[findpeaks] >Warning: Scaling not possible.')
    return X

# %%
def _togray(X, verbose=3):
    try:
        if verbose>=3: print('[findpeaks] >Conversion to gray image.')
        X = cv2.cvtColor(X, cv2.COLOR_BGR2GRAY)
    except:
        if verbose>=2: print('[findpeaks] >Warning: Conversion to gray not possible.')
    return X

# %%
def _denoise(X, h=10, verbose=3):
    try:
        if len(X.shape)==2:
            if verbose>=3: print('[findpeaks] >Denoising gray image.')
            X = cv2.fastNlMeansDenoising(X, h=h)
        if len(X.shape)==3:
            if verbose>=3: print('[findpeaks] >Denoising color image.')
            X = cv2.fastNlMeansDenoisingColored(X, h=h)
    except:
        if verbose>=2: print('[findpeaks] >Warning: Denoising not possible.')
    return X

# %%
def _resize(X, resize=None, verbose=3):
    try:
        if resize is not None:
            if verbose>=3: print('[findpeaks] >Resizing image to %s.' %(str(resize)))
            X = cv2.resize(X, resize)
    except:
        if verbose>=2: print('[findpeaks] >Warning: Resizing not possible.')
    return X

# %%
def _compute_with_topology(X, verbose=3):
    """Determine peaks in 2d-array using toplogy method.
    
    Description
    -----------
    A simple Python implementation of the 0-th dimensional persistent homology for 2D images.
    It is based on a two-dimensional persistent topology for peak detection.


    Parameters
    ----------
    X : numpy array
        2D array.

    Returns
    -------
    g0 : list
        Detected peaks.
    xx : numpy-array
        Meshgrid coordinates.
    yy : numpy-array
        Meshgrid coordinates.
    
    References
    ----------
    * https://www.sthu.org/code/codesnippets/imagepers.html
    * H. Edelsbrunner and J. Harer, Computational Topology. An Introduction, 2010, ISBN 0-8218-4925-5.

    """
    if verbose>=3: print('[findpeaks] >Compute using topology method..')
    # Compute meshgrid
    xx, yy = np.mgrid[0:X.shape[0], 0:X.shape[1]]
    # Compute persistence
    g0 = imagepers.persistence(X)
    # Return
    return g0, xx, yy

# %%
def _compute_with_mask(X, mask=0, verbose=3):
    """Determine peaks in 2d-array using a mask.
    
    Description
    -----------
    Takes an image and detect the peaks using the local maximum filter.
    Returns a boolean mask of the peaks (i.e. 1 when
    the pixel's value is the neighborhood maximum, 0 otherwise)

    Parameters
    ----------
    X : numpy array
        2D array.
    mask : float, (default : 0)
        Values <= mask are set as background.

    Returns
    -------
    detected_peaks : numpy array
        2D boolean array. True represents the detected peaks.
    
    References
    ----------
    * https://stackoverflow.com/questions/3684484/peak-detection-in-a-2d-array

    """
    if verbose>=3: print('[findpeaks] >Compute using mask (=%d) method..' %(mask))
    # define an 8-connected neighborhood
    neighborhood = generate_binary_structure(2,2)

    # apply the local maximum filter; all pixel of maximal value in their neighborhood are set to 1
    local_max = maximum_filter(X, footprint=neighborhood)==X
    # local_max is a mask that contains the peaks we are looking for, but also the background.
    # In order to isolate the peaks we must remove the background from the mask.

    # we create the mask of the background
    background = (X<=mask)

    # Erode the background in order to successfully subtract it form local_max, otherwise a line will 
    # appear along the background border (artifact of the local maximum filter)
    eroded_background = binary_erosion(background, structure=neighborhood, border_value=1)

    # We obtain the final mask, containing only peaks, by removing the background from the local_max mask (xor operation)
    detected_peaks = local_max ^ eroded_background
    
    # Return
    return detected_peaks

# %%
def plot(out, figsize=(15,8)):
    if out is None:
        print('[findpeaks] Nothing to plot.')
        return
    elif out['method']=='peaks1d':
        ax = plot1d(out, figsize=figsize)
    elif out['method']=='peaks2d':
        ax = plot2d(out, figsize=figsize)

def plot1d(out, figsize=(15,8)):
    if out.get('min_peaks',None) is not None:
        ax1 = _plot_original(out['Xorig'], out['xs'], out['labx'], out['min_peaks'][:,0].astype(int), out['max_peaks'][:,0].astype(int), title='Data', figsize=figsize)
        # ax1.set_title('Original')
    ax2 = _plot_original(out['X_s'], out['xs_s'], out['labx_s'], out['min_peaks_s'][:,0].astype(int), out['max_peaks_s'][:,0].astype(int), title='Data', figsize=figsize)
    # ax2.set_title('Final')

def plot2d(out, figsize=(15,8)):
    # Plot preprocessing steps
    plot_preprocessing(out)
    # Setup figure
    ax1,ax2,ax3 = plot_mask(out)
    # Plot persistence
    ax3,ax4 = plot_peristence(out)
    # Plot mesh
    ax5 = plot_mesh(out)

# %%
def plot_preprocessing(results, verbose=3):
    _ = preprocessing(results['Xorig'], mask=results['args']['mask'], scale=results['args']['scale'], denoise=results['args']['denoise'], togray=results['args']['togray'], resize=results['args']['resize'], showfig=True, verbose=3)

# %%
def plot_mask(results, verbose=3):
    fig, (ax1,ax2,ax3) = plt.subplots(1,3)
    # Original image
    togray = cmap='gray' if results['args']['togray'] else None
    
    ax1.imshow(results['Xorig'], cmap=togray, interpolation="nearest")
    ax1.invert_yaxis()
    ax1.set_title('Original')

    # Preprocessing
    ax2.imshow(results['Xproc'], cmap=togray, interpolation="nearest")
    ax2.invert_yaxis()
    ax2.set_title('Processed image')

    # Masking
    ax3.imshow(results['Xmask'], cmap=togray, interpolation="nearest")
    ax3.invert_yaxis()
    ax3.set_title('After Masking')
    return ax1,ax2,ax3

# %%
def plot_mesh(results, rstride=2, cstride=2, figsize=(15,8), cmap=plt.cm.hot_r, verbose=3):
    if not isinstance(results, dict):
        if verbose>=3: print('[findpeaks] >Nothing to plot. Hint: run the fit() function.')

    if verbose>=3: print('[findpeaks] >Plotting 3d-mesh..')
    # Plot the figure
    fig = plt.figure(figsize=figsize)
    ax = fig.gca(projection='3d')
    ax.plot_wireframe(results['xx'], results['yy'], results['Xproc'], rstride=rstride, cstride=cstride, linewidth=0.8)
    ax.set_xlabel('x-axis')
    ax.set_ylabel('y-axis')
    ax.set_zlabel('z-axis')
    plt.show()

    # Plot the figure
    fig = plt.figure(figsize=figsize)
    ax = fig.gca(projection='3d')
    ax.plot_surface(results['xx'], results['yy'], results['Xproc'], rstride=rstride, cstride=cstride, cmap=cmap, linewidth=0)
    ax.set_xlabel('x-axis')
    ax.set_ylabel('y-axis')
    ax.set_zlabel('z-axis')
    plt.show()
    return ax

# %%
def plot_peristence(results, figsize=(15,8), verbose=3):
    if not isinstance(results, dict):
        if verbose>=3: print('[findpeaks] >Nothing to plot. Hint: run the fit() function.')

    # Make the figure
    fig, (ax1,ax2) = plt.subplots(1,2, figsize=figsize)
    # Plot the detected loci
    if verbose>=3: print('[findpeaks] >Plotting loci of birth..')
    ax1.set_title("Loci of births")
    for i, homclass in tqdm(enumerate(results['g0'])):
        p_birth, bl, pers, p_death = homclass
        if pers <= 20.0:
            continue
        y, x = p_birth
        ax1.plot([x], [y], '.', c='b')
        ax1.text(x, y+0.25, str(i+1), color='b')

    ax1.set_xlim((0,results['Xproc'].shape[1]))
    ax1.set_ylim((0,results['Xproc'].shape[0]))
    plt.gca().invert_yaxis()
    ax1.grid(True)

    # Plot the persistence
    if verbose>=3: print('[findpeaks] >Plotting Peristence..')
    ax2.set_title("Peristence diagram")
    ax2.plot([0,255], [0,255], '-', c='grey')
    for i, homclass in tqdm(enumerate(results['g0'])):
        p_birth, bl, pers, p_death = homclass
        if pers <= 1.0:
            continue

        x, y = bl, bl-pers
        ax2.plot([x], [y], '.', c='b')
        ax2.text(x, y+2, str(i+1), color='b')

    ax2.set_xlabel("Birth level")
    ax2.set_ylabel("Death level")
    ax2.set_xlim((-5,260))
    ax2.set_ylim((-5,260))
    ax2.grid(True)
    return ax1, ax2


# %%
def _plot_original(X, xs, labx, min_peaks, max_peaks, title=None, figsize=(15,8)):
    uilabx = np.unique(labx)
    uilabx = uilabx[~np.isnan(uilabx)]

    fig,ax = plt.subplots(figsize=figsize)
    plt.plot(xs, X, 'k')
    plt.plot(max_peaks, X[max_peaks], "x", label='Top')
    plt.plot(min_peaks, X[min_peaks], "o", label='Bottom')

    # Color each detected label
    s=np.arange(0,len(X))
    for i in uilabx:
        idx=(labx==i)
        plt.plot(s[idx], X[idx], label='peak' + str(i))
    
    if len(uilabx)<=10:
        plt.legend(loc=0)
    plt.title(title)
    plt.grid(True)

# %% Import example dataset from github.
def import_example(data='2dpeaks', url=None, sep=';', verbose=3):
    """Import example dataset from github source.
    
    Description
    -----------
    Import one of the few datasets from github source or specify your own download url link.

    Parameters
    ----------
    data : str
        Name of datasets: '2dpeaks'
    url : str
        url link to to dataset.
    verbose : int, (default: 3)
        Print message to screen.

    Returns
    -------
    pd.DataFrame()
        Dataset containing mixed features.

    """
    if url is None:
        url='https://erdogant.github.io/datasets/'+data+'.zip'
    else:
        data = wget.filename_from_url(url)

    if url is None:
        if verbose>=3: print('[findpeaks] >Nothing to download.')
        return None

    curpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    PATH_TO_DATA = os.path.join(curpath, wget.filename_from_url(url))
    if not os.path.isdir(curpath):
        os.makedirs(curpath, exist_ok=True)

    # Check file exists.
    if not os.path.isfile(PATH_TO_DATA):
        if verbose>=3: print('[findpeaks] >Downloading [%s] dataset from github source..' %(data))
        wget.download(url, curpath)

    # Import local dataset
    if verbose>=3: print('[findpeaks] >Import dataset [%s]' %(data))
    df = pd.read_csv(PATH_TO_DATA, sep=sep)
    # Return
    return df
